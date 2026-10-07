# CineMind Cold-Start Evaluation Report

**Evaluation Protocol:** 200 sampled test viewers with >=20 train ratings; ground truth = cold-start movies (0 train ratings) rated >=4.0 in test period.

## 1. Metric Summary Table

| Retrieval Configuration | HitRate@5 | HitRate@10 | NDCG@5 | NDCG@10 | Recall@50 | Calls / Rec | Sec / Rec |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Similarity-Only (ARAG)** | 0.7600 | 0.7600 | 0.3904 | 0.3904 | 1.0000 | 5.0 | 0.02s |
| **Hybrid (CineMind)** | 0.7400 | 0.7400 | 0.3928 | 0.3928 | 1.0000 | 4.0 | 0.02s |
| **Graph-Only** | 0.8000 | 0.8000 | 0.4203 | 0.4203 | 1.0000 | 4.0 | 0.00s |

## 2. Hypothesis Verdict

**Verdict: Hybrid Graph Retrieval Did Not Exceed Similarity-Only.**

The content-based description embeddings captured sufficient semantic overlap to discover cold-start candidates directly from profile summaries.

## 3. Failure & Error Analysis (10 Exemplar Cases)

### Case 1 (Viewer #2)
- **Target Ground Truth:** `Past Lives`
- **Similarity-Only Hit@5:** No | Top Recommendations: Toy Story, Dune, Oppenheimer
- **Hybrid Hit@5:** No | Top Recommendations: Toy Story, Dune, Oppenheimer

### Case 2 (Viewer #3)
- **Target Ground Truth:** `Challengers`
- **Similarity-Only Hit@5:** No | Top Recommendations: Toy Story, Interstellar, Oppenheimer
- **Hybrid Hit@5:** No | Top Recommendations: Toy Story, Interstellar, Civil War

### Case 3 (Viewer #4)
- **Target Ground Truth:** `Past Lives`
- **Similarity-Only Hit@5:** No | Top Recommendations: Inception, Oppenheimer, Dune: Part Two
- **Hybrid Hit@5:** No | Top Recommendations: Inception, Civil War, Oppenheimer

### Case 4 (Viewer #9)
- **Target Ground Truth:** `Civil War, Challengers`
- **Similarity-Only Hit@5:** No | Top Recommendations: Interstellar, Oppenheimer, Dune: Part Two
- **Hybrid Hit@5:** Yes | Top Recommendations: Interstellar, Civil War, Oppenheimer

### Case 5 (Viewer #15)
- **Target Ground Truth:** `Challengers`
- **Similarity-Only Hit@5:** No | Top Recommendations: Inception, Oppenheimer, Dune: Part Two
- **Hybrid Hit@5:** No | Top Recommendations: Inception, Oppenheimer, Civil War

### Case 6 (Viewer #16)
- **Target Ground Truth:** `Past Lives`
- **Similarity-Only Hit@5:** No | Top Recommendations: Oppenheimer, Dune: Part Two, Poor Things
- **Hybrid Hit@5:** No | Top Recommendations: Oppenheimer, Dune: Part Two, Civil War

### Case 7 (Viewer #19)
- **Target Ground Truth:** `Challengers`
- **Similarity-Only Hit@5:** No | Top Recommendations: The Matrix, Arrival, Oppenheimer
- **Hybrid Hit@5:** No | Top Recommendations: The Matrix, Oppenheimer, Arrival

### Case 8 (Viewer #22)
- **Target Ground Truth:** `Civil War`
- **Similarity-Only Hit@5:** No | Top Recommendations: Oppenheimer, Dune: Part Two, Poor Things
- **Hybrid Hit@5:** No | Top Recommendations: Oppenheimer, Dune: Part Two, Gone Girl

### Case 9 (Viewer #28)
- **Target Ground Truth:** `Civil War, Poor Things`
- **Similarity-Only Hit@5:** Yes | Top Recommendations: The Martian, Oppenheimer, Dune: Part Two
- **Hybrid Hit@5:** No | Top Recommendations: The Martian, Oppenheimer, Shutter Island

### Case 10 (Viewer #30)
- **Target Ground Truth:** `Past Lives`
- **Similarity-Only Hit@5:** No | Top Recommendations: The Martian, Oppenheimer, Dune: Part Two
- **Hybrid Hit@5:** No | Top Recommendations: The Martian, Dune: Part Two, Oppenheimer

