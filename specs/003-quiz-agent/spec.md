# Feature Specification: Quiz Agent

**Feature Branch**: `001-quiz-agent`
**Created**: 2026-05-23
**Updated**: 2026-06-08
**Status**: Active
**Input**: Teaching Agent passes a detailed topic explanation to the Quiz Agent. When the learner clicks the **Quiz** button in the UI, a question set is generated and displayed. The quiz contains MCQ questions (single-answer with radio buttons, multiple-answer with checkboxes) and 4 descriptive questions (150-word responses). On submission the quiz is auto-evaluated and scores are shown.

---

## Execution Flow (main)

```
1. Teaching Agent produces a detailed explanation of a topic and passes it to the Quiz Agent
   → If explanation missing or empty: ERROR "No teaching content provided"
2. Learner clicks the Quiz button in the UI
3. Quiz Agent ingests the explanation and extracts key concepts, facts, and definitions
4. Quiz Agent generates a question set:
   → MCQ single-answer questions  (radio buttons, 1 correct of 4 options)
   → MCQ multiple-answer questions (checkboxes, 2+ correct of 4–6 options)
   → 4 descriptive questions       (free-text, expected ~150 words each)
5. Quiz UI renders all questions in one scrollable view inside the AI Tutor shell
6. Learner answers all questions and clicks Submit
7. Quiz Agent evaluates:
   → MCQ answers auto-graded immediately
   → Descriptive answers graded against a rubric (key points coverage)
8. Results screen shows: overall score, per-question result with correct answer / rubric feedback,
   and a breakdown of marks per section (MCQ total, Descriptive total)
   → For each incorrect or partially-correct MCQ:
      • Single-answer: a dedicated explanation panel shows WHY the chosen option is wrong
        and a topic deep-dive explaining the concept behind the correct answer
      • Multiple-answer: for every option the learner got wrong (selected-but-incorrect OR
        unselected-but-correct), a per-option explanation panel is shown stating why that
        option is incorrect or why it should have been selected, plus a topic deep-dive
        for the overarching concept
9. Structured result (score, weak sub-concepts) is passed back to the Teaching Agent loop
```

---

## ⚡ Quick Guidelines

- ✅ Focus on WHAT the learner experiences and WHY the quiz exists
- ✅ Quiz must reinforce the exact topic taught — no out-of-scope questions
- ❌ Avoid implementation details (no model names, no SDKs, no DB schema)
- 👥 Written for product owners and educators reviewing the AI Tutor experience

---

## User Scenarios & Testing

### Primary User Story
As a learner using the AI Tutor app, after the Teaching Agent finishes explaining a topic in detail, I want to click the **Quiz** button and immediately see a quiz on that topic so that I can verify my understanding through MCQ questions and written descriptive answers, then see my score.

### Acceptance Scenarios

1. **Given** the Teaching Agent has produced a detailed explanation, **When** the learner clicks the Quiz button, **Then** a quiz is generated and displayed covering only the taught content, containing both MCQ types and exactly 4 descriptive questions.
2. **Given** a single-answer MCQ is displayed, **Then** exactly 4 options are shown as radio buttons and only one can be selected at a time.
3. **Given** a multiple-answer MCQ is displayed, **Then** options are shown as checkboxes with a visible hint "Select all that apply" and 2 or more correct answers exist.
4. **Given** a single-answer MCQ answer is correct on submission, **Then** it is marked correct with a brief explanation referencing the taught material.
5. **Given** a single-answer MCQ is answered incorrectly, **When** the results screen is shown, **Then** the learner sees: (a) the option they chose highlighted as wrong, (b) a concise explanation of *why that specific option is incorrect*, and (c) a topic deep-dive panel that explains the underlying concept and the correct answer in detail.
6. **Given** a multi-answer MCQ where only a subset of correct options are selected, **When** the learner submits, **Then** the question is marked partially correct with feedback identifying missed and incorrect choices, and each incorrectly-handled option (selected-but-wrong OR missed correct option) has its own explanation panel stating *why it is wrong or why it should have been chosen*, followed by a topic deep-dive covering the broader concept.
7. **Given** a multi-answer MCQ is answered with zero correct selections, **When** results are shown, **Then** every option receives an individual explanation panel and a single topic deep-dive is shown for the question's sub-concept.
8. **Given** a descriptive question, **When** the learner submits a free-text answer of approximately 150 words, **Then** it is graded against a rubric and the learner sees a numeric score, model answer, and qualitative feedback.
9. **Given** a descriptive answer is submitted with significantly fewer than ~150 words, **Then** a soft warning is shown before submission encouraging a more complete answer (submission is not blocked).
10. **Given** the learner clicks Submit, **When** the results screen appears, **Then** it shows: overall score (e.g. 18/30), MCQ section score, Descriptive section score, per-question correct answer or rubric feedback, per-option wrong-answer explanations for all incorrect/missed MCQ options, and a list of weak sub-concepts.

### Edge Cases
- Teaching content is too short to generate the minimum question set → show a clear message and ask the Teaching Agent for more depth before quizzing.
- Learner abandons mid-quiz → answers are preserved in session so the quiz can be resumed.
- Learner refreshes the page → MCQ selections and descriptive text entered so far are restored.
- Question generation produces ambiguous or duplicate questions → agent re-generates that question once before falling back to a safer template.
- Learner submits a descriptive answer with very few words → soft nudge is shown but submission is not blocked; rubric scoring reflects the thin answer naturally.
- All MCQs left unanswered on submit → inline validation highlights unanswered questions and blocks submission until all MCQs are answered (descriptive answers may be left blank).
- Accessibility: learners using keyboard-only or screen readers must be able to interact with radio buttons, checkboxes, and text areas.

---

## Requirements

### Functional Requirements

**Input & Generation**
- **FR-001**: System MUST accept the Teaching Agent's detailed explanation as the sole authoritative source for quiz content.
- **FR-002**: System MUST generate questions strictly grounded in the provided explanation; no external facts may be introduced.
- **FR-003**: Each generated quiz MUST contain: MCQ single-answer questions, MCQ multiple-answer questions, and exactly 4 descriptive questions.
- **FR-004**: The Quiz button in the Teaching Agent UI MUST trigger quiz generation; the quiz is not shown until the button is clicked.
- **FR-005**: System MUST tag every question with the sub-concept it tests so weak areas can be reported back to the Teaching Agent.

**Question Types & Behaviour**
- **FR-006**: MCQ single-answer questions MUST present exactly 4 options rendered as **radio buttons**; only one option may be selected.
- **FR-007**: MCQ multiple-answer questions MUST present 4–6 options rendered as **checkboxes** and MUST display the hint "Select all that apply" so the learner knows multiple selections are valid; 2 or more options are correct.
- **FR-008**: Descriptive questions MUST provide a multi-line text area and a word-count indicator. The target response length is **~150 words**; the UI MUST display a soft warning (not a blocker) when the answer is significantly shorter.
- **FR-009**: Each descriptive question MUST be backed by a key-points rubric used for grading; the rubric is not visible to the learner during the quiz.
- **FR-010**: All 4 descriptive questions MUST be on the same topic as the taught content and MUST each target a different sub-concept.

**Evaluation & Feedback**
- **FR-011**: MCQ single-answer questions MUST be auto-graded on submission (correct / incorrect).
- **FR-011a**: For every incorrectly-answered single-answer MCQ, the results screen MUST show:
  1. The learner's chosen option, visually marked as wrong.
  2. The correct option, visually marked as correct.
  3. A **"Why this option is wrong"** explanation panel — a concise, topic-grounded sentence explaining why the chosen distractor is incorrect.
  4. A **topic deep-dive panel** — a detailed explanation (3–5 sentences) of the underlying concept drawn from the Teaching Content, reinforcing why the correct answer is right.
- **FR-012**: MCQ multiple-answer questions MUST support partial credit: score = (correct selections − incorrect selections) / total correct options, floored at 0.
- **FR-012a**: For every partially-correct or fully-incorrect multiple-answer MCQ, the results screen MUST show, per option that was mishandled:
  - If the learner **selected a wrong option**: a **"Why this option is incorrect"** explanation panel specific to that distractor.
  - If the learner **missed a correct option**: a **"Why this option should have been selected"** explanation panel specific to that option.
  - After all per-option panels: a single **topic deep-dive panel** covering the broader concept for the question, drawn from the Teaching Content.
- **FR-013**: Each descriptive question MUST be graded against its rubric and produce: a numeric score (e.g. 0–5), a model answer, and qualitative feedback (e.g. "You covered X but missed Y").
- **FR-014**: After submission the results screen MUST display:
  - Overall score (e.g. 22 / 35) with percentage
  - MCQ section subtotal
  - Descriptive section subtotal (sum of 4 question scores)
  - Per-question result: the learner's answer, correct answer or model answer, and brief feedback
  - Per-option wrong-answer explanation panels and topic deep-dives for all incorrect/missed MCQ options (per FR-011a and FR-012a)
  - List of weak sub-concepts derived from wrong/low-scoring questions
- **FR-015**: The results screen MUST include a recommended next action (re-teach, advance, or practice more) based on the overall percentage.

**UI & Experience**
- **FR-016**: Quiz UI MUST follow the existing AI Tutor app's visual language (typography, colors, spacing, components, dark/light mode).
- **FR-017**: All questions MUST be displayed in a single scrollable view so the learner can see the full quiz at once; a progress/completion indicator shows how many questions have been answered.
- **FR-018**: MCQ single-answer options MUST use `<input type="radio">` (or equivalent accessible component); MCQ multiple-answer options MUST use `<input type="checkbox">`.
- **FR-019**: Each descriptive text area MUST display a live word count next to it (e.g. "87 / ~150 words").
- **FR-020**: The Submit button MUST be disabled until all MCQ questions have a selection; descriptive answers are optional for submission purposes.
- **FR-021**: Inline validation on Submit MUST highlight any unanswered MCQ questions and scroll to the first one.
- **FR-022**: UI MUST be fully keyboard-navigable (tab through radio buttons, checkboxes, text areas, submit) and meet the same accessibility bar as the rest of the AI Tutor app.

**Session & Integration**
- **FR-023**: Quiz state (MCQ selections, descriptive text) MUST persist within the learner's session so refreshes or brief disconnects do not lose work.
- **FR-024**: On completion, the Quiz Agent MUST return a structured result (score, weak sub-concepts, descriptive rubric outcomes) to the Teaching Agent so the tutoring loop can adapt.
- **FR-025**: Learners MUST be able to retake a quiz; a new attempt generates a fresh question set on the same topic.
- **FR-026**: Quiz history per topic (attempt date, overall score) MUST be viewable by the learner.

---

## Key Entities

- **Teaching Content**: The detailed topic explanation produced by the Teaching Agent. Passed directly to the Quiz Agent; the sole grounding source for all questions.
- **Quiz**: A generated collection of questions tied to one Teaching Content item and one learner session. Triggered by the learner clicking the Quiz button.
- **Question**: A single item with a type (`mcq-single` | `mcq-multi` | `descriptive`), prompt, options (for MCQs), sub-concept tag, and grading rubric.
  - `mcq-single`: 4 radio-button options, 1 correct. Each distractor carries a **wrong-answer explanation** (why it is incorrect) and each correct option carries a **correct-answer explanation**. The question also carries a **topic deep-dive** explanation used when the learner answers wrong.
  - `mcq-multi`: 4–6 checkbox options, 2+ correct, "Select all that apply" hint shown. Each option carries an individual **per-option explanation** (wrong-if-selected or correct-if-missed). The question also carries a **topic deep-dive** explanation shown once after all per-option panels.
  - `descriptive`: free-text area, target ~150 words, rubric-graded.
- **Answer**: A learner's response to a Question, including timestamp and evaluation result.
- **Quiz Result**: Aggregated outcome — overall score, MCQ subtotal, Descriptive subtotal (4 questions), per-question feedback, weak sub-concepts, and recommended next action.

---

## Quiz Metadata (UI Contract)

The Quiz Agent MUST attach a structured **`metadata`** block to every generated `Quiz` object.
The UI reads this block to render the quiz correctly without inspecting individual question payloads.

### Quiz-Level Metadata

| Field | Type | Description |
|---|---|---|
| `question_type_counts` | object | Map of `{ "mcq-single": n, "mcq-multi": n, "descriptive": n }` |
| `total_questions` | integer | Total number of questions in the quiz |
| `max_score` | integer | Maximum achievable score across all questions |
| `mcq_max_score` | integer | Maximum score from MCQ questions only |
| `descriptive_max_score` | integer | Maximum score from descriptive questions only |
| `ui_hints` | object | Rendering directives for the quiz UI (see below) |

### UI Hints

| Field | Type | Value | Description |
|---|---|---|---|
| `mcq_single_input` | string | `"radio"` | Input type for single-answer MCQ options |
| `mcq_multi_input` | string | `"checkbox"` | Input type for multiple-answer MCQ options |
| `mcq_multi_hint_text` | string | `"Select all that apply"` | Visible hint displayed above multi-answer options |
| `descriptive_target_words` | integer | `150` | Target word count shown in descriptive question UI |
| `descriptive_soft_warning_below` | integer | `80` | Word count threshold below which a soft warning appears |

### Question-Level Metadata (per Question)

Each `Question` object carries fields the UI uses to render and gate interactions:

| Field | Type | Present on | Description |
|---|---|---|---|
| `id` | string | all types | Unique question identifier (e.g. `"q1"`) |
| `type` | string | all types | `"mcq-single"` \| `"mcq-multi"` \| `"descriptive"` |
| `sub_concept` | string | all types | The topic sub-concept this question tests (used in weak-area reporting) |
| `max_points` | integer | all types | Maximum marks this question contributes to the total score |
| `topic_deep_dive` | string | MCQ types | Concept explanation shown to the learner after an incorrect MCQ answer |
| `rubric` | list of strings | `descriptive` | Key points used for grading (not shown to learner during the quiz) |

### Option-Level Metadata (per MCQ Option)

Each `MCQOption` carries fields that drive both rendering and post-submission feedback:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique option identifier within the question (e.g. `"q1a"`) |
| `text` | string | Display text shown to the learner |
| `is_correct` | boolean | Whether this option is a correct answer (hidden during quiz; revealed on submit) |
| `explanation` | string | Per-option feedback shown after submission: why the option is correct or why it is wrong / should have been selected |

### Result Metadata (QuizResult)

The `QuizResult` object returned after evaluation carries these fields the Teaching Agent and UI both consume:

| Field | Type | Description |
|---|---|---|
| `overall_score` | integer | Total marks earned across all questions |
| `max_score` | integer | Maximum possible score for the quiz |
| `overall_percentage` | float | `overall_score / max_score × 100`, rounded to one decimal |
| `mcq_subtotal` | integer | Marks earned from MCQ questions |
| `descriptive_subtotal` | integer | Marks earned from descriptive questions |
| `question_results` | list | Per-question outcome (see below) |
| `weak_sub_concepts` | list of strings | Sub-concept tags from questions scored below 50% — passed back to the Teaching Agent |
| `recommended_action` | string | `"re-teach"` (< 50%) \| `"practice-more"` (50–74%) \| `"advance"` (≥ 75%) |

### Question Result (per question, within QuizResult)

| Field | Type | Present on | Description |
|---|---|---|---|
| `question_id` | string | all | Reference back to the `Question.id` |
| `score` | number | all | Marks awarded for this question |
| `max_score` | integer | all | Maximum marks for this question |
| `is_correct` | boolean | MCQ single | True when the learner selected the correct option |
| `wrong_answer_explanation` | string | MCQ single (wrong) | Why the chosen option is incorrect |
| `topic_deep_dive` | string | MCQ (wrong/partial) | Concept deep-dive panel content |
| `per_option_explanations` | list | MCQ multi (wrong/partial) | One entry per mishandled option: `{ option_id, explanation_type ("wrong-selected"\|"missed-correct"), explanation }` |
| `model_answer` | string | descriptive | The rubric-derived ideal answer shown after submission |
| `feedback` | string | descriptive | Qualitative feedback referencing what the learner covered or missed |

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and learning outcomes
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded to quiz generation, delivery, and evaluation
- [x] Dependencies on the Teaching Agent and the app UI system are identified

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Review checklist passed
