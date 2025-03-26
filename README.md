# Social_Media_NER_TE_Drugs
A temporary repository to keep track of papers in literature review and show sample data. <br> <br>
CIS 830 Advanced Topics in AI  <br>
Kansas State University <br>

# Sample DATA & scripts

### 1. GPT3-Lexicon
- **Link/sample:** [GPT3-Lexicon Drugs of Abuse Lexicon](https://github.com/kristycarp/gpt3-lexicon/blob/main/lexicon/drugs_of_abuse_lexicon.tsv)
- **Contains:** **98 drugs** with an average of **~150 lexicon/synonym terms** (including common misspellings) per drug.
- **FYI:**  
-	To get these, they basically asked ChatGPT what are some possible synonyms to describe drug X, then verifies the term programmatically using Google API (within the first 10 pages of Google search).

---

### 2. All Reddit Posts- AcademicTorrents
- **Link:** [AcademicTorrents - Reddit Archive](https://academictorrents.com/details/ba051999301b109eab37d16f027b3f49ade2de13)
- **Overview:**  
 nearly every available Reddit post.
- **Sub-Reddit Filtering:**
  - Known drug related - Resulted in **91 subreddits** dating back to 2005.

---

### 3. Reddit‐impacts Paper
- **Sample: sample_Reddit‐impacts_data.csv**  
- **Link:** [Reddit‐impacts Paper](https://arxiv.org/abs/2405.06145) 
- **LABELED DATA:**
  - Binary **about illicit drug use** or **not** (plus metadata)

## Script 
Using **find_terms_in_subreddits.py**
- **Sample: sample_from_subReddit_5MeODMT.csv**  
- I simply searched every comment/submission for direct matches in GPT3-lexicon.
- Resulting in a dataframe
  - datetime
  - text
  - lexicon/synonym term
  - index term
---


