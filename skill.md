# PROJECT SPECIFICATION
# Agentic AI-Based Proactive Movie Recommendation System Using Dynamic User Preference Memory

Version: 1.0
Status: Draft — assumptions require review
Project type: Final-year undergraduate CSE project

---

# PART 1 — PRODUCT SPECIFICATION

## 1. Product overview

Build a web-based, agentic AI movie recommendation system that learns a user's evolving movie preferences and proactively delivers personalized movie recommendations.

The system must operate in the background. Users should not have to open a chatbot or submit a prompt to receive recommendations.

The system observes user-provided movie interactions, updates a persistent preference profile, identifies suitable unseen movies, and decides when to deliver a recommendation. It must provide an explanation for each recommendation and allow users to provide feedback.

The research foundation is the paper:

"Tunable LLM-based Proactive Recommendation Agent" (T-PRA), ACL 2025.

The proposed project adapts the paper's proactive recommendation approach to the movie domain and investigates an extension: dynamic user preference memory.

Before claiming faithful reproduction, inspect the paper and official implementation. Document which components are reproduced, adapted, or newly implemented.

## 2. Problem statement

Many recommendation systems primarily rely on historical preferences or require users to actively search for recommendations. User interests can change over time, so a static preference profile may continue recommending content that no longer matches the user's current interests.

This project investigates whether an agent that updates user preferences from recent interactions and proactively recommends movies can improve recommendation relevance, responsiveness to preference changes, and user experience.

The system will be evaluated against defined baselines using offline experiments and, where feasible, a small user study.

## 3. Goals

### Primary goals

1. Provide personalized movie recommendations without requiring a user prompt.
2. Maintain a persistent user preference profile.
3. Update that profile as new ratings, likes, dislikes, and watch events arrive.
4. Use a background process to generate or refresh recommendations.
5. Filter out movies the user has already watched or dismissed.
6. Explain why each movie was recommended.
7. Measure recommendation quality and adaptation to preference changes.
8. Compare the proposed dynamic-memory extension with a baseline.

### Secondary goals

1. Provide a dashboard showing recommendations and their explanations.
2. Allow users to configure recommendation frequency.
3. Allow users to pause or resume proactive recommendations.
4. Provide controls to inspect, correct, and reset their preference profile.
5. Provide a research dashboard for experiment results.

## 4. Non-goals

The first version will not:

- Stream or host full-length movies.
- Purchase movie tickets or subscriptions.
- Scrape streaming services or private user accounts.
- Infer viewing activity from a user's device without explicit permission.
- Run a large language model continuously.
- Train a foundation model from scratch.
- Guarantee that a recommendation will be liked.
- Claim research novelty or improved performance before experiments.
- Require a conversational interface.
- Implement a production-scale distributed infrastructure.

## 5. Target users

### Registered movie viewer

A user who rates movies, records watch history, and receives personalized recommendations.

### Project administrator

The project owner, who can inspect system health, background job status, dataset information, and experiment results.

Administrative access must be restricted and must not expose users' private information unnecessarily.

## 6. Core user journeys

### Journey A: New user onboarding

1. The user registers and signs in.
2. The system asks the user to select or rate a small set of movies.
3. The user may optionally select genres they like or dislike.
4. The system creates an initial preference profile.
5. The system generates an initial recommendation list.
6. The user sees recommendations on the dashboard.

Acceptance criteria:

- Given a valid registration, when the user submits the form, then an account is created.
- Given a new account, when onboarding is completed, then an initial preference profile exists.
- Given insufficient preference data, when recommendations are generated, then the system uses a clearly identified cold-start strategy.
- The system must not pretend that it has learned preferences that the user has not supplied.

### Journey B: Background preference learning

1. The user rates a movie, likes it, dislikes it, or records it as watched.
2. The interaction is stored with a timestamp and source.
3. The system schedules a preference-update job.
4. The preference service updates the user's profile.
5. The system records the profile version and update time.
6. The recommendation pipeline is triggered if the interaction warrants a refresh.

Acceptance criteria:

- Given a valid new interaction, when it is saved, then it is persisted exactly once.
- Given a new interaction, when the learning job succeeds, then the profile version advances.
- Reprocessing the same event must not create duplicate preference updates.
- If a learning job fails, it must be retryable without duplicating the interaction.
- A user's dislike must not be treated as a positive preference.

### Journey C: Proactive recommendation delivery

1. A background trigger determines that the user's recommendations need refreshing.
2. The system retrieves candidate movies.
3. It removes watched, dismissed, unavailable, and otherwise ineligible candidates.
4. The ranking process scores the remaining candidates.
5. The agent selects a recommendation set according to configured rules.
6. The system stores the recommendation batch and its reasons.
7. The user sees the recommendations in the dashboard.
8. If notifications are enabled, the system delivers an in-app notification.

Acceptance criteria:

- Recommendation generation does not require a user chat prompt.
- A recommendation batch is associated with the profile version used to generate it.
- Watched and dismissed movies are excluded.
- Repeated execution must not repeatedly notify the user about the same movie within the configured cooldown.
- Failed jobs must not produce a false success status.
- The user can disable notifications without losing access to the dashboard.

### Journey D: Preference change

1. The user's recent activity begins to differ from their older activity.
2. The system updates short-term preference signals.
3. The system retains longer-term preference information.
4. The ranking process uses both short-term and long-term signals.
5. The system evaluates whether recommendations should change.
6. New recommendations are generated when the trigger conditions are met.

Acceptance criteria:

- Recent interactions have a configurable influence on short-term preferences.
- Older interactions can continue to contribute to long-term preferences.
- The system can represent positive and negative preference signals.
- The system does not automatically erase long-term interests after one interaction.
- Preference-shift behavior can be tested using a reproducible dataset split or simulation.

### Journey E: User feedback

1. The user marks a recommendation as liked, disliked, watched, or not interested.
2. The feedback is stored.
3. The system updates preference signals and recommendation exclusions.
4. The next eligible recommendation cycle uses the updated information.

Acceptance criteria:

- Feedback is associated with the correct user and movie.
- A dismissed movie is not recommended again during the configured suppression period.
- Feedback can be corrected or removed where appropriate.
- The system explains that feedback affects future recommendations.

### Journey F: Pause, resume, and privacy controls

1. The user opens settings.
2. The user pauses recommendations, changes frequency, or disables notifications.
3. The system applies the new settings to future jobs.
4. The user can inspect and reset their preference profile.

Acceptance criteria:

- Paused users do not receive newly generated proactive notifications.
- Disabling notifications does not disable manual dashboard access.
- A settings change is enforced by the backend, not only hidden in the UI.
- Resetting preferences removes derived preference data while retaining only account data required for the application.
- Users can request account deletion.

## 7. Functional requirements

### FR-01 Authentication

The system must support account registration, login, logout, and protected routes.

### FR-02 Movie catalogue

The system must maintain a searchable movie catalogue containing a stable movie identifier, title, release year where available, genres, and dataset metadata.

### FR-03 User interactions

The system must support ratings, likes, dislikes, watched status, and recommendation dismissal.

### FR-04 Preference profile

The system must maintain a user-specific profile derived from available interactions.

### FR-05 Dynamic preference memory

The system must represent both longer-term preference signals and more recent preference signals. The relative contribution of each must be configurable and experimentally testable.

### FR-06 Candidate generation

The system must retrieve a candidate set of movies that the user has not watched or dismissed.

### FR-07 Recommendation ranking

The system must rank candidates using a reproducible scoring process. Any LLM-based ranking or reasoning must be documented separately from deterministic ranking components.

### FR-08 Agent decision

The agent must determine whether to generate or refresh recommendations based on defined events, schedules, and user settings.

### FR-09 Background execution

The system must process eligible jobs independently of an active browser session.

### FR-10 Recommendation explanations

Each recommendation must include a concise explanation grounded in available movie metadata and user preference signals. The system must not invent movie attributes.

### FR-11 Notifications

The system must display in-app notifications when a new recommendation batch is ready, subject to user settings.

### FR-12 Recommendation history

The system must store delivered recommendation batches, timestamps, model or algorithm version, and relevant profile version.

### FR-13 User controls

The user must be able to pause recommendations, configure frequency, dismiss movies, and reset preferences.

### FR-14 Experiment support

The system must support reproducible evaluation of baseline and extended recommendation approaches.

### FR-15 Observability

The system must record job status, failures, retry count, processing duration, and relevant experiment metadata without logging secrets or unnecessary personal data.

## 8. Non-functional requirements

### Performance

- Standard dashboard APIs should target a p95 response time below 500 ms under the defined local test load, excluding cold model startup and external model calls.
- Recommendation generation may be asynchronous.
- The UI must show pending, completed, and failed states for asynchronous operations.

### Reliability

- Background jobs must support retries.
- Event processing must be idempotent.
- Duplicate scheduled executions must not create duplicate notifications.
- A failed model call must not corrupt stored user preferences.

### Security

- Passwords must be securely hashed if password authentication is implemented.
- Secrets must be stored in environment variables or a secret manager.
- Every user-specific API must enforce ownership checks.
- Administrative endpoints must require authorization.
- Input must be validated on the server.
- Rate limits must protect authentication and feedback endpoints.

### Privacy

- Only collect data needed for recommendations and evaluation.
- Provide user controls for profile reset and account deletion.
- Do not collect browsing or streaming activity without explicit user action and permission.
- Avoid storing raw prompts or sensitive data unless necessary.
- Make the source of preference signals inspectable.

### Accessibility and usability

- Core workflows must work on desktop and mobile layouts.
- Forms must have labels and validation messages.
- Recommendation cards must be keyboard accessible.
- Loading, empty, and error states must be implemented.

## 9. Recommendation behavior

### Inputs

- Explicit movie ratings.
- Likes and dislikes.
- Watched status.
- Dismissal feedback.
- Movie genres and available metadata.
- Timestamps of interactions.
- Optional initial genre preferences.

### Preference representation

Maintain two conceptual preference components:

1. Long-term profile: stable signals accumulated over a longer history.
2. Short-term profile: recent interactions that may reflect changing interests.

The initial implementation may use time-decayed interaction weights. The exact decay function and combination weights are experimental parameters, not established facts.

An example formulation to evaluate is:

weight(interaction) = interaction_strength × exp(-decay_rate × interaction_age)

The system must define how ratings, likes, dislikes, and watched events map to interaction_strength. Do not treat this illustrative formula as a verified component of T-PRA.

### Candidate selection

- Retrieve movies matching positive preferences.
- Consider genre and item similarity.
- Exclude movies already watched or dismissed.
- Avoid returning duplicate movie IDs.
- Apply a configurable diversity constraint.
- Return fewer than the requested number if there are not enough eligible candidates.

### Ranking

The system should start with a deterministic, reproducible baseline. The agentic extension may use an LLM to select, refine, or explain candidates.

The final score must be inspectable. Store enough information to reproduce why a movie was ranked.

### Proactive trigger policy

For the MVP, trigger recommendation refreshes on:

- A meaningful new user interaction.
- Completion of onboarding.
- A scheduled refresh, if enabled.
- A significant preference-profile change.

Use a cooldown to avoid excessive notifications. The trigger policy must be configurable.

Do not run an LLM continuously. Invoke it only when a recommendation job requires it.

## 10. Dataset and evaluation

### Dataset

Use MovieLens as the initial movie-rating dataset.

Dataset source: https://grouplens.org/datasets/movielens/

Select a specific MovieLens release and record its exact name, download date, license/usage conditions, and preprocessing steps in the project documentation.

Do not assume the dataset contains real-time viewing events. User activity and preference changes may need to be simulated from timestamped historical ratings.

### Data split

Use a time-aware split where feasible:

- Earlier interactions form the initial user history.
- Later interactions form the evaluation period.
- Do not allow future interactions to leak into the preference profile used for earlier recommendations.

Document user and item filtering, cold-start handling, and any minimum-interaction threshold.

### Baselines

At minimum, compare:

1. Popularity-based recommendations.
2. A conventional collaborative-filtering or content-based baseline.
3. The base-paper-inspired implementation without the proposed dynamic-memory extension.
4. The extended dynamic-memory approach.

The exact baseline implementation must be documented.

### Metrics

- Precision@K.
- Recall@K.
- NDCG@K.
- Catalog coverage.
- Recommendation diversity, if implemented.
- Preference-shift adaptation quality.
- Recommendation generation latency.
- Notification count and duplicate-notification rate.

Define each metric and its averaging method before running experiments.

### Preference-shift experiment

Construct a reproducible evaluation in which a user's recent preferences differ from their earlier preferences.

Compare how quickly and accurately each method adapts to the later preference period.

Clearly distinguish simulated preference shifts from naturally occurring preference changes.

### Research integrity

- Report actual measured results only.
- Do not fabricate scores or user-study outcomes.
- Record random seeds and configuration.
- Include negative or inconclusive results.
- Avoid claiming that the extension is novel until the literature review supports that claim.

---

# PART 2 — TECHNICAL PLAN

## 11. Proposed architecture

Use a modular monolith for the MVP, with a separate background worker process. Avoid microservices unless a measured requirement justifies them.

### Components

1. Next.js frontend
2. Backend API
3. PostgreSQL database
4. Movie catalogue and retrieval module
5. Preference-memory module
6. Recommendation ranking module
7. Agent orchestration module
8. Background job queue and worker
9. Notification module
10. Experiment and evaluation scripts

### High-level data flow

User interaction
  -> API validation
  -> PostgreSQL interaction record
  -> enqueue preference-update job
  -> worker updates preference profile
  -> evaluate recommendation trigger
  -> enqueue recommendation job
  -> retrieve candidates
  -> filter and rank candidates
  -> optional LLM agent reasoning
  -> persist recommendation batch
  -> create in-app notification
  -> dashboard displays recommendation

### Suggested technology choices

Frontend:
- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui

Backend:
- Python FastAPI for the research and recommendation API
- Pydantic for request and response validation

Database:
- PostgreSQL

Background processing:
- Redis-backed queue, such as RQ or Celery
- Redis used for queueing and transient job state, not as the only persistent store

Recommendation research:
- Python
- pandas and NumPy
- scikit-learn or a suitable recommendation library
- PyTorch/Transformers only where required by the selected base implementation

Model:
- Follow the base paper's documented model and inference/training requirements.
- Keep model access behind a provider interface.
- Support a local model configuration where feasible.
- Do not make the entire application dependent on the LLM being available.

Deployment:
- Docker Compose for local development.
- Separate web, API, worker, PostgreSQL, and Redis services.
- Document GPU/model requirements separately.

These are proposed implementation choices. Verify the official T-PRA repository's actual dependencies before locking the final environment.

## 12. Architecture boundaries

### Frontend

Responsible for:
- Authentication screens.
- Onboarding.
- Movie search and rating.
- Recommendation dashboard.
- Recommendation explanations.
- Feedback controls.
- Notification center.
- User settings.
- Research dashboard, if enabled.

The frontend must not contain recommendation-ranking business logic or secret API keys.

### API

Responsible for:
- Authentication and authorization.
- Validating user actions.
- Persisting interactions.
- Returning movie and recommendation data.
- Enqueuing background jobs.
- Exposing job and notification status.
- Applying user settings.

### Preference service

Responsible for:
- Loading user interaction history.
- Calculating long-term and short-term preference signals.
- Updating profile versions.
- Producing an inspectable preference summary.
- Supporting profile reset.

### Recommendation service

Responsible for:
- Candidate retrieval.
- Watched/dismissed filtering.
- Ranking.
- Diversity constraints.
- Explanation generation.
- Persisting recommendation results.

### Agent orchestration

Responsible for:
- Determining which recommendation tools to call.
- Applying trigger and cooldown policies.
- Invoking model reasoning when necessary.
- Validating agent output.
- Falling back to deterministic recommendations if the LLM fails.

The agent must not be allowed to execute arbitrary code, arbitrary SQL, or unrestricted external actions.

### Background worker

Responsible for:
- Processing preference-update jobs.
- Processing recommendation jobs.
- Retrying transient failures.
- Enforcing idempotency.
- Updating job status.
- Avoiding duplicate notification delivery.

## 13. Initial data model

Use UUID primary keys unless the selected dataset requires stable external IDs. Preserve MovieLens IDs as external identifiers.

### User

- id
- email
- password_hash or external_auth_id
- created_at
- updated_at
- status

### UserSettings

- user_id
- recommendations_enabled
- notifications_enabled
- refresh_frequency
- notification_cooldown
- created_at
- updated_at

### Movie

- id
- movielens_id
- title
- release_year, nullable
- genres
- metadata_json, nullable
- created_at

Constraints:
- movielens_id must be unique.
- Required fields must be validated during import.

### UserInteraction

- id
- user_id
- movie_id
- interaction_type
- rating, nullable
- occurred_at
- source
- idempotency_key, nullable
- created_at

Constraints:
- Validate interaction_type against a defined enum.
- Rating must be within the supported range.
- Prevent duplicate ingestion of the same event where an idempotency key is provided.

### UserPreferenceProfile

- id
- user_id
- profile_version
- long_term_preferences_json
- short_term_preferences_json
- computed_at
- algorithm_version

Constraints:
- profile_version must increase monotonically for successful updates.
- Store the algorithm version used to calculate the profile.

### RecommendationBatch

- id
- user_id
- profile_version
- algorithm_version
- trigger_type
- status
- created_at
- completed_at, nullable

### RecommendationItem

- id
- batch_id
- movie_id
- rank
- score
- explanation
- feedback_status, nullable
- created_at

Constraints:
- A movie may appear only once per batch.
- Rank must be unique within a batch.
- Score must be finite.
- Explanation must be grounded in known metadata and profile signals.

### Notification

- id
- user_id
- recommendation_batch_id
- notification_type
- status
- deduplication_key
- created_at
- delivered_at, nullable

Constraints:
- deduplication_key must prevent duplicate delivery for the same logical notification.
- Respect user notification settings.

### BackgroundJob

- id
- job_type
- user_id, nullable
- idempotency_key
- status
- attempts
- scheduled_at
- started_at, nullable
- completed_at, nullable
- last_error, nullable

Constraints:
- Track retries and terminal failures.
- Do not store secrets in error messages.

## 14. API contract

Use versioned routes under /api/v1.

The exact authentication mechanism is an implementation decision. All protected routes must validate identity and ownership.

### Authentication

POST /api/v1/auth/register
- Creates an account.
- Returns account summary and session information.
- Returns 400 for invalid input and 409 for an existing account.

POST /api/v1/auth/login
- Authenticates a user.
- Returns 401 for invalid credentials.

POST /api/v1/auth/logout
- Invalidates the active session where applicable.

GET /api/v1/me
- Returns the authenticated user's profile and settings.

### Movies

GET /api/v1/movies
- Query: search, genre, page, page_size.
- Returns paginated movie results.

GET /api/v1/movies/{movie_id}
- Returns movie details.

### Interactions

POST /api/v1/interactions
- Body: movie_id, interaction_type, rating?, occurred_at?, idempotency_key?
- Persists interaction and enqueues relevant jobs.
- Returns 201 for a new interaction.
- Returns a defined idempotent response for a duplicate event.

GET /api/v1/interactions
- Returns the authenticated user's interaction history with pagination.

DELETE /api/v1/interactions/{interaction_id}
- Deletes or retracts an interaction according to the documented policy.
- Recomputes affected preferences.

### Recommendations

GET /api/v1/recommendations
- Returns the latest eligible recommendation batch.

GET /api/v1/recommendations/{batch_id}
- Returns a batch and its items.
- Must enforce user ownership.

POST /api/v1/recommendations/refresh
- Requests a refresh.
- Enqueues a job; does not block on model generation.
- Returns 202 with job information.

POST /api/v1/recommendations/{recommendation_id}/feedback
- Body: liked, disliked, watched, or dismissed.
- Persists feedback and schedules an update.

### Preferences

GET /api/v1/preferences
- Returns an inspectable preference summary.

POST /api/v1/preferences/reset
- Resets derived preference data after confirmation.
- Must not delete another user's data.

### Settings

GET /api/v1/settings
- Returns user settings.

PATCH /api/v1/settings
- Updates allowed settings.
- Validates frequency and notification options.

### Jobs and notifications

GET /api/v1/jobs/{job_id}
- Returns status only to the job owner or authorized administrator.

GET /api/v1/notifications
- Returns the user's notifications.

POST /api/v1/notifications/{notification_id}/read
- Marks a notification as read.

Do not expose internal stack traces, secrets, raw model credentials, or another user's records through any API.

## 15. Background job design

### Job types

- preference.update
- recommendation.generate
- notification.create
- catalogue.import
- experiment.run (restricted to research/admin use)

### Job lifecycle

queued -> running -> succeeded

Transient failure:
running -> retry_wait -> queued

Terminal failure:
running -> failed

### Requirements

- Each job must have a stable idempotency key.
- Use bounded retries with backoff.
- Do not retry permanent validation errors indefinitely.
- Store job status and failure reason.
- Ensure only one logical recommendation batch is generated for a given idempotency key.
- Use database transactions for related persistent writes.
- A notification should be created only after the recommendation batch is successfully persisted.
- The system must recover safely if a worker stops mid-job.

## 16. Agent design

The agent is a controlled workflow, not an unrestricted autonomous system.

### Inputs

- User preference profile.
- Recent interaction summary.
- Candidate movie records.
- User settings.
- Previously delivered recommendations.

### Available tools

1. get_user_preferences
2. retrieve_movie_candidates
3. get_movie_metadata
4. filter_watched_movies
5. filter_dismissed_movies
6. rank_candidates
7. save_recommendation_batch
8. create_notification

Tools must enforce user scope and validate arguments.

### Agent workflow

1. Receive a recommendation job.
2. Load the profile version and settings.
3. Retrieve candidate movies.
4. Apply eligibility filters.
5. Rank candidates using the configured method.
6. Optionally use the LLM to select or explain candidates.
7. Validate the structured output.
8. Persist the batch.
9. Create an eligible in-app notification.
10. Record execution metadata.

### LLM output contract

The model should return structured data containing:
- selected movie IDs
- ordered ranking
- concise explanation for each selection
- preference signals used
- optional reason for skipping recommendation generation

Reject unknown movie IDs, malformed output, unsupported claims, and excessive recommendation counts.

The deterministic system remains responsible for eligibility, authorization, persistence, and notification rules.

### Fallback behavior

If the LLM is unavailable:
- Use the deterministic ranking baseline.
- Mark the batch as generated using fallback mode.
- Do not claim LLM reasoning was used.
- Record the failure in observability data.

## 17. Dynamic preference memory plan

Implement this as a separable module so the baseline and extension can be compared.

### Baseline memory

Use a profile computed from the user's available historical interactions without the proposed recency-sensitive adjustment.

### Extended memory

Maintain:
- Long-term preference signals.
- Short-term preference signals.
- Timestamped interaction evidence.
- Profile version and computation timestamp.

Potential implementation:
- Convert genres or item features into preference vectors.
- Assign positive and negative weights to interactions.
- Apply a configurable time-decay function to short-term signals.
- Combine short-term and long-term scores with configurable parameters.
- Normalize scores where appropriate.

### Required experiments

Vary:
- Decay rate.
- Short-term/long-term combination weight.
- Number of recent interactions considered.
- Recommendation refresh threshold.

Evaluate:
- Overall ranking quality.
- Performance before and after simulated preference shifts.
- Adaptation speed.
- Stability when a single noisy interaction occurs.

Avoid selecting parameters using the test set.

## 18. Security and privacy plan

- Use authenticated sessions or tokens with secure handling.
- Validate all request bodies.
- Enforce ownership checks on every user-specific resource.
- Store password hashes, never plaintext passwords.
- Keep model keys out of frontend bundles and source control.
- Restrict administrative and experiment endpoints.
- Apply rate limits to login, feedback, and refresh requests.
- Use parameterized database operations or a safe ORM.
- Avoid arbitrary tool execution by the LLM.
- Do not trust LLM output without schema validation.
- Provide a clear data reset and account deletion process.
- Do not log sensitive user data unnecessarily.

## 19. Testing strategy

### Unit tests

- Interaction validation.
- Rating validation.
- Preference-weight calculations.
- Time-decay calculations.
- Candidate filtering.
- Ranking determinism.
- Duplicate-event handling.
- Cooldown logic.
- LLM output validation.

### Integration tests

- Interaction persistence and job enqueueing.
- Worker updates to preference profiles.
- Recommendation generation and persistence.
- Notification creation.
- Retry and recovery behavior.
- User ownership enforcement.
- Profile reset.

### End-to-end tests

- Register, onboard, and receive recommendations.
- Rate a movie and verify background processing.
- Dislike a movie and verify suppression.
- Pause recommendations and verify no new proactive notification.
- Resume recommendations and verify normal processing.
- Reset preference data.
- Handle a model failure gracefully.

### Research validation

- Reproducible data preprocessing.
- Time-aware train/validation/test split.
- No future-data leakage.
- Baseline comparisons.
- Ablation of dynamic memory.
- Preference-shift experiment.
- Report confidence intervals or variability where feasible.
- Record model, dataset, and configuration versions.

## 20. Deployment and configuration

Provide:
- Docker Compose configuration.
- Database migrations.
- Dataset import script.
- Environment variable example file without real secrets.
- API startup command.
- Worker startup command.
- Frontend startup command.
- Test commands.
- Model setup instructions.
- Experiment reproduction instructions.

The project must be runnable locally without requiring paid external services for the basic deterministic recommender.

LLM-based features may require a locally available model or a separately configured model endpoint.

---

# PART 3 — IMPLEMENTATION TASK BREAKDOWN

Tasks should be completed in order. Each task must be independently testable. Do not attempt to implement the entire project in one code-generation step.

## Phase 0: Research and feasibility

### Task 0.1 — Inspect the base paper
- Read the full T-PRA paper.
- Identify its problem formulation, agent architecture, training procedure, datasets, evaluation metrics, and limitations.
- Record the exact components to reproduce.

Acceptance:
- A research notes document exists.
- Claims in the project description are traceable to the paper.
- Adaptations are distinguished from reproduced components.

### Task 0.2 — Inspect the official repository
- Clone the official T-PRA repository.
- Review its README, dependencies, model requirements, dataset scripts, training scripts, and evaluation code.
- Identify incompatibilities with the target movie dataset.

Acceptance:
- A reproducible environment plan exists.
- All required model files and datasets are identified.
- Any inaccessible or incompatible component is documented.

### Task 0.3 — Run a minimal base experiment
- Follow the official instructions on a small supported subset.
- Record hardware, runtime, errors, and outputs.

Acceptance:
- The experiment either runs successfully or produces a documented blocker and alternative plan.
- No results are fabricated.

## Phase 1: Repository and infrastructure

### Task 1.1 — Establish project structure
- Create frontend, backend, worker, research, and documentation directories.
- Add formatting, linting, and test commands.

Acceptance:
- All services have documented startup commands.
- Basic lint and test commands run.

### Task 1.2 — Configure local infrastructure
- Add PostgreSQL and Redis to Docker Compose.
- Configure health checks and persistent local database storage.

Acceptance:
- Services start from a clean checkout.
- Health checks report readiness.
- No credentials are committed.

### Task 1.3 — Configure database migrations
- Create initial schema and migration workflow.

Acceptance:
- A fresh database can be initialized from migrations.
- Tests can use an isolated database.

## Phase 2: Catalogue and accounts

### Task 2.1 — Import MovieLens data
- Select a specific MovieLens release.
- Write a repeatable import script.
- Preserve source movie IDs.

Acceptance:
- Import is repeatable.
- Duplicate movie IDs are rejected or safely handled.
- Import summary reports rows accepted and rejected.

### Task 2.2 — Implement authentication
- Registration, login, logout, and current-user endpoint.

Acceptance:
- Valid users can authenticate.
- Invalid credentials return the documented error.
- Protected endpoints reject unauthenticated requests.

### Task 2.3 — Implement movie catalogue APIs
- Search, genre filters, pagination, and movie detail.

Acceptance:
- Search and pagination behave correctly.
- Invalid pagination parameters are rejected.
- Users cannot access arbitrary database internals.

## Phase 3: Interactions and preferences

### Task 3.1 — Implement interaction APIs
- Ratings, likes, dislikes, watched status, and dismissal.

Acceptance:
- Invalid interactions are rejected.
- Valid interactions are persisted.
- Duplicate idempotency keys do not duplicate events.

### Task 3.2 — Implement baseline preference profile
- Calculate a reproducible profile from interaction history.

Acceptance:
- The same input and configuration produce the same profile.
- Profile version and algorithm version are stored.

### Task 3.3 — Implement dynamic preference memory
- Add short-term and long-term preference components.
- Add configurable recency weighting.

Acceptance:
- Recent and older signals can be inspected separately.
- Parameter changes alter the profile as expected.
- Unit tests cover decay and preference combination.

### Task 3.4 — Add profile reset
- Allow users to reset derived preferences.

Acceptance:
- Only the owner's profile is reset.
- Reset behavior is tested.
- Interaction retention behavior follows the documented policy.

## Phase 4: Recommendation engine

### Task 4.1 — Implement candidate retrieval
- Retrieve candidates using the available preference and catalogue data.

Acceptance:
- Candidate IDs are valid.
- Watched and dismissed items are filtered.
- Empty candidate sets are handled.

### Task 4.2 — Implement deterministic baseline ranking
- Implement a documented content-based, collaborative, or hybrid baseline.

Acceptance:
- Ranking is deterministic for fixed inputs.
- Scores are inspectable.
- Unit tests cover ranking and ties.

### Task 4.3 — Implement recommendation batches
- Persist ordered recommendation results and explanations.

Acceptance:
- No duplicate movie exists in a batch.
- Every recommendation belongs to the correct user.
- Batch metadata records profile and algorithm versions.

### Task 4.4 — Integrate the base-paper method
- Adapt the selected T-PRA components to the movie recommendation setting.
- Keep base-paper components separable from the proposed extension.

Acceptance:
- The implementation mapping to the paper is documented.
- Any deviations are explicit.
- The system can run the base-inspired configuration independently.

### Task 4.5 — Add LLM integration and fallback
- Add structured model output and validation.
- Retain deterministic fallback behavior.

Acceptance:
- Malformed model output is rejected.
- Unknown movie IDs are rejected.
- Model failure does not prevent baseline recommendations.

## Phase 5: Background agent

### Task 5.1 — Create background job infrastructure
- Define job types, states, idempotency, retries, and backoff.

Acceptance:
- Jobs can be enqueued and processed.
- Duplicate jobs do not duplicate logical results.
- Failures are visible and retryable.

### Task 5.2 — Implement preference-update worker
- Consume interaction events and update profiles.

Acceptance:
- New interactions trigger profile updates.
- Reprocessing is safe.
- Profile update failures are observable.

### Task 5.3 — Implement recommendation worker
- Generate recommendation batches asynchronously.

Acceptance:
- The API returns without waiting for full model generation.
- Job status can be queried.
- Worker restart does not corrupt a batch.

### Task 5.4 — Implement proactive trigger policy
- Add event-driven and scheduled refresh triggers.
- Add cooldown and deduplication.

Acceptance:
- Eligible events trigger refresh.
- Cooldown suppresses repeated notifications.
- Paused users do not receive proactive notifications.

### Task 5.5 — Implement notification creation
- Create in-app notifications after successful batch persistence.

Acceptance:
- No notification is created for a failed batch.
- Duplicate notification attempts are idempotent.
- User notification settings are respected.

## Phase 6: Frontend

### Task 6.1 — Build onboarding
- Registration, preference selection, and initial ratings.

Acceptance:
- User can complete onboarding.
- Empty and validation states are visible.

### Task 6.2 — Build movie catalogue UI
- Search, filter, and rate movies.

Acceptance:
- User actions reach the backend.
- Loading, empty, and error states work.

### Task 6.3 — Build recommendation dashboard
- Show movie cards, ranking, explanations, and feedback controls.

Acceptance:
- Recommendations render from persisted backend data.
- Feedback updates the UI and backend.
- Watched and dismissed states are reflected.

### Task 6.4 — Build notifications and settings
- Notification center, pause/resume, frequency, and profile reset.

Acceptance:
- Settings persist across sessions.
- Backend behavior matches UI settings.
- User can pause and resume recommendations.

### Task 6.5 — Build job status UI
- Show pending, completed, and failed recommendation refreshes.

Acceptance:
- Status is obtained from the backend.
- Failed jobs do not appear as successful.

## Phase 7: Evaluation

### Task 7.1 — Build reproducible preprocessing
- Create time-aware splits and document filtering.

Acceptance:
- No future interactions leak into training profiles.
- The split can be recreated from a recorded seed/configuration.

### Task 7.2 — Implement metric calculations
- Precision@K, Recall@K, NDCG@K, and selected secondary metrics.

Acceptance:
- Metrics are unit-tested on hand-checkable examples.
- The evaluation protocol documents aggregation.

### Task 7.3 — Run baseline comparisons
- Compare popularity, conventional recommender, and base-inspired agent.

Acceptance:
- All methods use the same evaluation split.
- Results and configurations are saved.

### Task 7.4 — Evaluate dynamic memory
- Compare the base-inspired method with and without the extension.

Acceptance:
- Preference-shift evaluation is reproducible.
- Results include parameter settings.
- Conclusions match measured results.

### Task 7.5 — Perform ablation and robustness checks
- Test different decay rates, memory weights, and noisy feedback scenarios.

Acceptance:
- Ablation results are recorded.
- Limitations and negative results are documented.

## Phase 8: Quality and delivery

### Task 8.1 — Security review
- Review authentication, ownership checks, secrets, and input validation.

Acceptance:
- Cross-user access tests pass.
- Secrets are absent from source control.
- Protected routes enforce authentication.

### Task 8.2 — End-to-end testing
- Test onboarding through proactive recommendation and feedback.

Acceptance:
- Core user journeys pass.
- Model failure and worker failure are tested.

### Task 8.3 — Documentation
- Write setup, architecture, API, research methodology, and experiment reproduction guides.

Acceptance:
- A new developer can run the application using the documentation.
- The base-paper adaptation and extension are clearly described.

### Task 8.4 — Final demonstration
- Prepare a demonstration using seeded users and reproducible interactions.

Acceptance:
- Demonstration does not depend on unpredictable external activity.
- Background processing and preference changes are visible.
- Reported results match stored experiment outputs.

---

# PART 4 — ASSUMPTIONS TO REVIEW

## High impact

### A1. T-PRA reproducibility
Assumption: The official repository can be run in the available environment.

Impact: HIGH

Review by: Inspect dependencies, model requirements, data availability, and run a small experiment before committing to the implementation.

If false: Reproduce the feasible core method, document deviations, and obtain faculty approval for the adapted methodology.

### A2. Meaning of "agentic"
Assumption: A controlled workflow that observes events, chooses tools, updates preferences, and initiates recommendations qualifies for the project's agentic-AI objective.

Impact: HIGH

Review by: Confirm the department's expectations for agentic AI.

### A3. Novelty of dynamic preference memory
Assumption: The proposed memory extension is suitable as a project contribution.

Impact: HIGH

Review by: Conduct a focused literature review. Treat it as a hypothesis until related work is examined.

### A4. Dataset suitability
Assumption: MovieLens has sufficient timestamped interactions to support offline evaluation and a simulated preference-shift experiment.

Impact: HIGH

Review by: Select a dataset version and inspect sparsity, timestamps, and available metadata.

### A5. Evaluation acceptance
Assumption: Offline recommendation metrics and simulated preference shifts are acceptable for the academic project.

Impact: HIGH

Review by: Confirm evaluation requirements with the faculty supervisor.

## Medium impact

### A6. Stack
Assumption: Next.js, FastAPI, PostgreSQL, and Redis are acceptable.

Impact: MEDIUM

Correct if: The supervisor or team requires a different stack.

### A7. Notifications
Assumption: In-app notifications are sufficient for the MVP; email and push notifications are optional.

Impact: MEDIUM

Correct if: External notification delivery is a required feature.

### A8. Authentication
Assumption: Standard email/password authentication is sufficient.

Impact: MEDIUM

Correct if: Institutional login or OAuth is required.

### A9. Model deployment
Assumption: The model can run locally or through a configurable endpoint, and the baseline recommender remains usable without it.

Impact: MEDIUM

Correct if: Offline-only execution is mandatory.

### A10. User study
Assumption: A small user study is optional, subject to faculty approval and available participants.

Impact: MEDIUM

Correct if: Human evaluation is mandatory.

## Low impact

### A11. Initial recommendation count
Assumption: Show approximately 10 recommendations per batch.

Impact: LOW

### A12. Refresh schedule
Assumption: Support event-driven updates and an optional daily refresh, with user-configurable cooldowns.

Impact: LOW

### A13. Single-user development environment
Assumption: The first deployment targets a small demonstration workload, not production-scale traffic.

Impact: LOW

---

# PART 5 — DEFINITION OF DONE

The MVP is complete when:

1. A user can register and complete onboarding.
2. MovieLens data is imported reproducibly.
3. Users can record ratings and feedback.
4. The system maintains persistent preference memory.
5. A background worker updates the profile after interactions.
6. Recommendations are generated without a chat prompt.
7. Watched and dismissed movies are excluded.
8. Recommendations and explanations appear in the dashboard.
9. User settings control proactive notifications.
10. Job failures, retries, and duplicate events are handled safely.
11. The base-inspired approach and dynamic-memory extension can be evaluated separately.
12. The evaluation uses a documented time-aware split and reproducible metrics.
13. Setup and experiment reproduction instructions are complete.
14. The report distinguishes measured results, assumptions, adaptations, and limitations.

---

# PART 6 — INSTRUCTIONS TO THE CODING AGENT

You are implementing this project incrementally.

Before writing code:
1. Inspect the base paper and official repository.
2. Inspect the current repository structure.
3. Identify conflicts between this specification and the existing codebase.
4. Report high-impact assumptions that need confirmation.
5. Propose the first small implementation task.

During implementation:
- Do not implement every phase in one pass.
- Work on one task at a time.
- Read the existing code before changing it.
- Follow the existing project conventions unless they conflict with this specification.
- Do not silently change API contracts or data models.
- Add tests for each behavior.
- Keep the deterministic baseline functional even if the LLM is unavailable.
- Never fabricate experimental results.
- Never claim exact paper reproduction without evidence.
- Keep research code and production application code appropriately separated.
- Update documentation when behavior changes.

For each task, report:
1. What changed.
2. Files created or modified.
3. Tests executed and their results.
4. Any deviations from the specification.
5. Remaining risks or blockers.

Start with Phase 0, Task 0.1: inspect the T-PRA paper and repository. Do not begin full implementation until the base method, environment, and adaptation plan are understood.
