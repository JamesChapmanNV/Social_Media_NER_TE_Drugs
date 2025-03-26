''''
Some of this came from the following source:
https://github.com/Watchful1/PushshiftDumps/blob/master/scripts/filter_file.py

Then uses large regex to find terms 
'''
import zstandard
import os
import json
import csv
import re
from datetime import datetime
import logging
import logging.handlers
from concurrent.futures import ProcessPoolExecutor, as_completed

log = logging.getLogger("bot")
log.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)
log.addHandler(stream_handler)
file_handler = logging.FileHandler("bot.log", mode="w")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
log.addHandler(file_handler)

def load_lexicon(csv_path):

    lexicon_dict = {}
    # I ignored these because they had thousands of hits
    # Also, I ignored less than 4 characters
    ignorelist = ['most', 'diet', 'hard', 'pain', 'tolerance', 'second']

    with open(csv_path, newline='', encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            index_term = row["index term"].strip().strip("'\"")
            index_term = index_term.replace("_", " ")
            
            synonyms_str = row["GPT-3 synonyms"].strip()
            # Split the synonyms string by commas (each term is enclosed in quotes)
            terms = [term.strip() for term in synonyms_str.split(",")]
            synonyms_list = []
            for term in terms:
                # Remove quotes and replace underscores with spaces
                term = term.strip("'\"").replace("_", " ")
                term = term.strip()
                # Only add that are at least 4 characters long and not in the blocklist
                if len(term) >= 4 and term not in ignorelist:
                    synonyms_list.append(term)
                    
            # Add index term to the synonyms list 
            if index_term not in synonyms_list:
                synonyms_list.append(index_term)
            
            # duplicates
            synonyms_list = list(set(synonyms_list))
            lexicon_dict[index_term] = synonyms_list
    return lexicon_dict


def build_regex_and_mapping(lexicon):
    """
    Build a mapping from each synonym (and the index term itself) to the index term.
    Then compile one regex pattern that matches any synonym.
    """
    term_to_index = {}
    for index_term, synonyms in lexicon.items():
        term_to_index[index_term.lower()] = index_term
        for syn in synonyms:
            term_to_index[syn.lower()] = index_term
    # Build a regex that matches any synonym (with word boundaries for accuracy).
    pattern = re.compile(r'\b(' + '|'.join(re.escape(term) for term in term_to_index.keys()) + r')\b', re.IGNORECASE)
    return pattern, term_to_index

def read_and_decode(reader, chunk_size, max_window_size, previous_chunk=None, bytes_read=0):
    chunk = reader.read(chunk_size)
    bytes_read += chunk_size
    if previous_chunk is not None:
        chunk = previous_chunk + chunk
    try:
        return chunk.decode("utf-8")
    except UnicodeDecodeError:
        if bytes_read > max_window_size:
            raise UnicodeError(f"Unable to decode frame after reading {bytes_read:,} bytes")
        return read_and_decode(reader, chunk_size, max_window_size, chunk, bytes_read)

def read_lines_zst(file_name):
    with open(file_name, 'rb') as file_handle:
        buffer = ''
        reader = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(file_handle)
        while True:
            chunk = read_and_decode(reader, 2**27, (2**29) * 2)
            if not chunk:
                break
            lines = (buffer + chunk).split("\n")
            for line in lines[:-1]:
                yield line, file_handle.tell()
            buffer = lines[-1]
        reader.close()

def process_file(filename, folder_path, output_folder, pattern, term_to_index):
    """
    Process one .zst file:
      - Decompress the file and read lines.
      - For each JSON line, extract the text (from 'selftext' for submissions or 'body' for comments).
      - Use the regex to find any matching term.
      - Write a CSV row if any term was found.
    """
    input_file_path = os.path.join(folder_path, filename)
    output_filename = filename.replace(".zst", ".csv")
    output_file_path = os.path.join(output_folder, output_filename)
    
    try:
        base, suffix = filename.rsplit("_", 1)
        subreddit_name = base
        file_type = suffix.replace(".zst", "")
    except Exception as e:
        log.error(f"Filename {filename} does not match expected format: {e}")
        return

    fields = ["created", "text", "index_terms", "terms"]
    file_size = os.stat(input_file_path).st_size
    file_lines, bad_lines = 0, 0
    last_created = None

    with open(output_file_path, "w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(fields)
        try:
            for line, file_bytes_processed in read_lines_zst(input_file_path):
                try:
                    obj = json.loads(line)
                    if file_type == "submissions":
                        text = obj.get('selftext', "")
                    else:
                        text = obj.get('body', "")
                    text_lower = text.lower()
                    # Use the compiled regex to find all matches in one go.
                    matches = pattern.findall(text_lower)
                    if not matches:
                        continue
                    found_index_terms = set()
                    found_terms = []
                    for match in matches:
                        index_term = term_to_index.get(match.lower())
                        if index_term:
                            found_index_terms.add(index_term)
                            found_terms.append(match)
                    if not found_index_terms:
                        continue
                    created = datetime.fromtimestamp(int(obj['created_utc'])).strftime("%Y-%m-%d %H:%M")
                    last_created = created
                    writer.writerow([str(created), str(text), str(list(found_index_terms)), str(found_terms)])
                except json.JSONDecodeError:
                    bad_lines += 1
                file_lines += 1
                if file_lines % 100000 == 0:
                    percent = (file_bytes_processed / file_size) * 100
                    log.info(f"{last_created} : {file_lines:,} lines processed : {bad_lines:,} bad lines : {percent:.0f}%")
        except KeyError as err: 
            log.info(f"Object has no key: {err}")
        except Exception as err:
            log.info(err)

    log.info(f"Complete for {filename}: {file_lines:,} lines processed, {bad_lines:,} bad lines. Output: {output_file_path}")

if __name__ == "__main__":
    # Load lexicon CSV containing the lexicon for drugs of abuse.
    lexicon_csv = r"C:\Users\James\OneDrive\Documents\GitHub\Social_Media_NER_TE_Drugs\drugs_of_abuse_lexicon.csv"
    lexicon = load_lexicon(lexicon_csv)
    pattern, term_to_index = build_regex_and_mapping(lexicon)
    
    # Folder containing your .zst files.
    folder_path =   r"C:\Users\James\OneDrive\Kansas State University\CIS 830\Project_SparKG\data\reddit\torrent\reddit\subreddits24"
    output_folder = r"C:\Users\James\OneDrive\Kansas State University\CIS 830\Project_SparKG\data\reddit\torrent\reddit\filtered_csvs"
    
    files = [f for f in os.listdir(folder_path) if f.endswith(".zst")]
    
    # Process each file concurrently using a process pool.
    with ProcessPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(process_file, filename, folder_path, output_folder, pattern, term_to_index) for filename in files]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                log.error(e)
