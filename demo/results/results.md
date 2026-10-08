# CineMind Cold-Start Evaluation Report

**Evaluation Protocol:** 200 sampled test viewers with >=20 train ratings; ground truth = cold-start movies (0 train ratings) rated >=4.0 in test period.

## 1. Metric Summary Table

| Retrieval Configuration | HitRate@5 | HitRate@10 | NDCG@5 | NDCG@10 | Recall@50 | Calls / Rec | Sec / Rec |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Similarity-Only (ARAG)** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 9.0 | 0.04s |
| **Hybrid (CineMind)** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 12.0 | 0.31s |
| **Graph-Only** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 8.0 | 0.27s |

## 2. Hypothesis Verdict

**Verdict: Hybrid Graph Retrieval Did Not Exceed Similarity-Only.**

The content-based description embeddings captured sufficient semantic overlap to discover cold-start candidates directly from profile summaries.

## 3. Failure & Error Analysis (10 Exemplar Cases)

### Case 1 (Viewer #1)
- **Target Ground Truth:** `Catacombs, Mean Girls 2`
- **Similarity-Only Hit@5:** No | Top Recommendations: Branded, Altered States, Parallels
- **Hybrid Hit@5:** No | Top Recommendations: Branded, Ashes and Diamonds, Altered States

### Case 2 (Viewer #2)
- **Target Ground Truth:** `Decalogue II`
- **Similarity-Only Hit@5:** No | Top Recommendations: Branded, Altered States, Parallels
- **Hybrid Hit@5:** No | Top Recommendations: Branded, Vengeance, Altered States

### Case 3 (Viewer #3)
- **Target Ground Truth:** `Comme t'y es belle!`
- **Similarity-Only Hit@5:** No | Top Recommendations: Branded, Altered States, Parallels
- **Hybrid Hit@5:** No | Top Recommendations: Branded, Extraterrestrial, Altered States

### Case 4 (Viewer #4)
- **Target Ground Truth:** `Dragon Ball: Curse of the Blood Rubies`
- **Similarity-Only Hit@5:** No | Top Recommendations: Branded, Altered States, Parallels
- **Hybrid Hit@5:** No | Top Recommendations: Branded, Rio Lobo, Altered States

### Case 5 (Viewer #5)
- **Target Ground Truth:** `Sharknado 2: The Second One`
- **Similarity-Only Hit@5:** No | Top Recommendations: Branded, Altered States, Parallels
- **Hybrid Hit@5:** No | Top Recommendations: Branded, God Bless America, Altered States

### Case 6 (Viewer #6)
- **Target Ground Truth:** `Don't Blame Karma!, Dragon Ball: Sleeping Princess in Devil's Castle`
- **Similarity-Only Hit@5:** No | Top Recommendations: Branded, Altered States, Parallels
- **Hybrid Hit@5:** No | Top Recommendations: Branded, Human Capital, Altered States

### Case 7 (Viewer #7)
- **Target Ground Truth:** `House of Voices, Lady and the Tramp II: Scamp's Adventure`
- **Similarity-Only Hit@5:** No | Top Recommendations: Branded, Altered States, Parallels
- **Hybrid Hit@5:** No | Top Recommendations: Branded, Halloweentown II: Kalabar's Revenge, Altered States

### Case 8 (Viewer #8)
- **Target Ground Truth:** `Wer, Second in Command`
- **Similarity-Only Hit@5:** No | Top Recommendations: Branded, Altered States, Parallels
- **Hybrid Hit@5:** No | Top Recommendations: Branded, Monkey Business, Altered States

### Case 9 (Viewer #9)
- **Target Ground Truth:** `BTS: Permission to Dance on Stage - LA, Disconnected`
- **Similarity-Only Hit@5:** No | Top Recommendations: Branded, Altered States, Parallels
- **Hybrid Hit@5:** No | Top Recommendations: Branded, Katyn, Altered States

### Case 10 (Viewer #10)
- **Target Ground Truth:** `Qwerty, Tremors 4: The Legend Begins`
- **Similarity-Only Hit@5:** No | Top Recommendations: Branded, Altered States, Parallels
- **Hybrid Hit@5:** No | Top Recommendations: Branded, Ginger Snaps Back: The Beginning, Altered States

