"""Comprehensive Mermaid diagram pipeline tests.

Tests every layer a diagram passes through before reaching the UI:
  1. sanitize_mermaid_labels() — fence-stripping then label quoting
  2. validate_mermaid()        — structural validation
  3. sanitize → validate combined (what the agent does)
  4. _resolve_diagram() via TeachingAgent (full fallback logic, monkeypatched)

All tests are fully offline — no LLM calls, no Kafka.
"""

from __future__ import annotations

import pytest

import teaching_agent.agent as agent_module
from teaching_agent.helpers import sanitize_mermaid_labels
from teaching_agent.validators import validate_mermaid

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

def _noop(field, token):
    pass


def _make_stream(diagram_body: str):
    """Build a minimal streaming response containing the given diagram body."""
    md = (
        "**Explanation**\nSome explanation text.\n\n"
        f"**Diagram**\n{diagram_body}\n\n"
        "**Notes**\nKey point one.\n\n"
        "**Example**\nA worked example."
    )
    return iter([(ch, 0) for ch in md])


def _run_agent(monkeypatch, diagram_body: str, mode: str = "beginner",
               retry_response: str | None = None):
    """Run the teaching agent with a fixed streaming diagram.

    Returns the TeachingAgentOutput so callers can assert on .content.diagram.
    retry_response: if provided, used as the call_llm (non-streaming) return value
    for the beginner retry path.
    """
    monkeypatch.setenv("TEACHING_MODEL", "fake/model")
    monkeypatch.setattr(
        "teaching_agent.guardrail.call_llm",
        lambda msgs, cfg: ('{"category": "valid_question", "reason": "ok"}', 0),
    )
    monkeypatch.setattr(
        "teaching_agent.agent.call_llm_stream",
        lambda msgs, cfg: _make_stream(diagram_body),
    )
    if retry_response is not None:
        monkeypatch.setattr(
            "teaching_agent.agent.call_llm",
            lambda msgs, cfg: (retry_response, 0),
        )
    monkeypatch.setattr(
        "teaching_agent.agent.get_max_reflection_iterations",
        lambda m: 0,
    )
    out, _ = agent_module.TeachingAgent().run(
        {"topic": "Test topic", "output_mode": mode}, _noop
    )
    return out


def _pipeline(raw: str) -> bool:
    """Convenience: sanitize then validate (mirrors what the agent does)."""
    return validate_mermaid(sanitize_mermaid_labels(raw))


# ===========================================================================
# 1. FENCE STRIPPING — sanitize_mermaid_labels()
# ===========================================================================

class TestFenceStripping:
    """Verify that ``` / ```mermaid fences are removed before validation."""

    # --- matching fences ---

    def test_strips_mermaid_fence_basic(self):
        raw = "```mermaid\ngraph TD\n  A --> B\n```"
        assert sanitize_mermaid_labels(raw) == "graph TD\n  A --> B"

    def test_strips_plain_fence_basic(self):
        raw = "```\ngraph TD\n  A --> B\n```"
        assert sanitize_mermaid_labels(raw) == "graph TD\n  A --> B"

    def test_strips_mermaid_fence_multiline(self):
        body = "graph TD\n  A --> B\n  B --> C\n  C --> D"
        raw = f"```mermaid\n{body}\n```"
        assert sanitize_mermaid_labels(raw) == body

    def test_strips_fence_with_trailing_whitespace_on_close(self):
        raw = "```mermaid\ngraph TD\n  A --> B\n```   "
        result = sanitize_mermaid_labels(raw.strip())
        assert result == "graph TD\n  A --> B"

    def test_strips_fence_with_space_after_mermaid_keyword(self):
        raw = "```mermaid  \ngraph TD\n  A --> B\n```"
        result = sanitize_mermaid_labels(raw)
        assert result == "graph TD\n  A --> B"

    def test_strips_sequence_diagram_fence(self):
        raw = "```mermaid\nsequenceDiagram\n  Alice ->> Bob: Hello\n  Bob -->> Alice: Hi\n```"
        result = sanitize_mermaid_labels(raw)
        assert result.startswith("sequenceDiagram")
        assert "```" not in result

    def test_strips_flowchart_fence(self):
        raw = "```mermaid\nflowchart LR\n  A --> B --> C\n```"
        result = sanitize_mermaid_labels(raw)
        assert result.startswith("flowchart LR")

    def test_strips_class_diagram_fence(self):
        raw = "```mermaid\nclassDiagram\n  Animal <|-- Duck\n```"
        result = sanitize_mermaid_labels(raw)
        assert result.startswith("classDiagram")

    def test_strips_state_diagram_fence(self):
        raw = "```mermaid\nstateDiagram-v2\n  [*] --> Active\n  Active --> [*]\n```"
        result = sanitize_mermaid_labels(raw)
        assert result.startswith("stateDiagram-v2")

    def test_strips_er_diagram_fence(self):
        raw = "```mermaid\nerDiagram\n  CUSTOMER ||--o{ ORDER : places\n```"
        result = sanitize_mermaid_labels(raw)
        assert result.startswith("erDiagram")

    def test_strips_pie_fence(self):
        raw = '```mermaid\npie\n  title Pie Chart\n  "Slice A" : 40\n```'
        result = sanitize_mermaid_labels(raw)
        assert result.startswith("pie")

    def test_strips_mindmap_fence(self):
        raw = "```mermaid\nmindmap\n  root((Topic))\n    SubA\n    SubB\n```"
        result = sanitize_mermaid_labels(raw)
        assert result.startswith("mindmap")

    def test_strips_timeline_fence(self):
        raw = "```mermaid\ntimeline\n  title History\n  2020 : Event A\n```"
        result = sanitize_mermaid_labels(raw)
        assert result.startswith("timeline")

    # --- non-matching / pass-through ---

    def test_no_fence_unchanged(self):
        plain = "graph TD\n  A --> B\n  B --> C"
        assert sanitize_mermaid_labels(plain) == plain

    def test_single_backtick_not_stripped(self):
        raw = "`graph TD\n  A --> B`"
        # Single backticks are not a code fence — should pass through
        result = sanitize_mermaid_labels(raw)
        assert result == raw

    def test_text_before_fence_not_stripped(self):
        # Fence is not at start — regex does not match, content left as-is
        raw = "Here is a diagram:\n```mermaid\ngraph TD\n  A --> B\n```"
        result = sanitize_mermaid_labels(raw)
        assert "Here is a diagram" in result

    def test_unclosed_fence_not_stripped(self):
        raw = "```mermaid\ngraph TD\n  A --> B"
        result = sanitize_mermaid_labels(raw)
        # No closing ```, regex does not match
        assert "```mermaid" in result


# ===========================================================================
# 2. LABEL QUOTING — sanitize_mermaid_labels()
# ===========================================================================

class TestLabelQuoting:
    """Every special character that triggers label quoting, individually and combined."""

    def _has_quoted(self, diagram: str, inner: str) -> bool:
        return f'["{inner}"]' in sanitize_mermaid_labels(diagram)

    # --- individual special characters ---

    def test_colon_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[Step: One] --> B[End]", "Step: One")

    def test_open_paren_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[Result (n)] --> B[End]", "Result (n)")

    def test_close_paren_alone_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[OK)] --> B[End]", "OK)")

    def test_open_brace_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[Set{x}] --> B[End]", "Set{x}")

    def test_close_brace_alone_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[End}] --> B[X]", "End}")

    def test_hash_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[Node #1] --> B[End]", "Node #1")

    def test_percent_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[50% done] --> B[End]", "50% done")

    def test_division_sign_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[a÷b] --> B[End]", "a÷b")

    def test_multiplication_sign_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[a×b] --> B[End]", "a×b")

    def test_less_or_equal_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[x≤y] --> B[End]", "x≤y")

    def test_greater_or_equal_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[x≥y] --> B[End]", "x≥y")

    def test_not_equal_triggers_quoting(self):
        assert self._has_quoted("graph TD\n  A[x≠y] --> B[End]", "x≠y")

    # --- multiple special chars in one label ---

    def test_multiple_specials_in_one_label(self):
        d = "graph TD\n  A[Step: Result (ok)] --> B[End]"
        result = sanitize_mermaid_labels(d)
        assert '["Step: Result (ok)"]' in result

    def test_all_specials_in_one_label(self):
        d = "graph TD\n  A[a:b(c)d{e}f#g%h÷i×j≤k≥l≠m] --> B[End]"
        result = sanitize_mermaid_labels(d)
        assert result.count('[') == 2  # two labels; both processed
        assert '"' in result

    # --- already-quoted labels ---

    def test_already_quoted_colon_untouched(self):
        d = 'graph TD\n  A["Step: One"] --> B[End]'
        result = sanitize_mermaid_labels(d)
        assert result.count('"') == 2  # still exactly one quoted label

    def test_already_quoted_no_extra_wrapping(self):
        d = 'graph TD\n  A["A: B"] --> B["C: D"]'
        result = sanitize_mermaid_labels(d)
        assert '["A: B"]' in result
        assert '["C: D"]' in result
        assert '["["' not in result  # no double-wrapping

    # --- mixed labels ---

    def test_plain_label_unchanged(self):
        d = "graph TD\n  A[PlainLabel] --> B[AnotherPlain]"
        assert sanitize_mermaid_labels(d) == d

    def test_mixed_labels_only_special_quoted(self):
        d = "graph TD\n  A[Plain] --> B[Step: Two] --> C[Plain2]"
        result = sanitize_mermaid_labels(d)
        assert "A[Plain]" in result
        assert 'B["Step: Two"]' in result
        assert "C[Plain2]" in result

    # --- inner double quotes escaped ---

    def test_inner_double_quotes_escaped(self):
        d = 'graph TD\n  A[Step: "init"] --> B[End]'
        result = sanitize_mermaid_labels(d)
        assert 'A["Step: &quot;init&quot;"]' in result

    # --- fence stripping + label quoting together ---

    def test_fenced_diagram_labels_still_quoted(self):
        raw = "```mermaid\ngraph TD\n  A[Step: One] --> B[End (ok)]\n```"
        result = sanitize_mermaid_labels(raw)
        assert result.startswith("graph TD")
        assert '["Step: One"]' in result
        assert '["End (ok)"]' in result

    def test_fenced_all_plain_labels_unchanged(self):
        raw = "```mermaid\ngraph TD\n  A[Start] --> B[End]\n```"
        result = sanitize_mermaid_labels(raw)
        assert "A[Start]" in result
        assert "B[End]" in result


# ===========================================================================
# 3. STRUCTURAL VALIDATION — validate_mermaid()
# ===========================================================================

class TestValidateMermaidValid:
    """All recognized Mermaid diagram types with realistic content."""

    # --- graph (all 5 directions) ---

    def test_graph_td(self):
        assert validate_mermaid("graph TD\n  A --> B --> C")

    def test_graph_lr(self):
        assert validate_mermaid("graph LR\n  A --> B")

    def test_graph_tb(self):
        assert validate_mermaid("graph TB\n  A --> B")

    def test_graph_rl(self):
        assert validate_mermaid("graph RL\n  A --> B")

    def test_graph_bt(self):
        assert validate_mermaid("graph BT\n  A --> B")

    def test_graph_with_labels(self):
        assert validate_mermaid(
            'graph TD\n  A["Input"] --> B["Process"]\n  B --> C["Output"]'
        )

    def test_graph_with_subgraph(self):
        assert validate_mermaid(
            "graph TD\n  subgraph Group\n    A --> B\n  end\n  B --> C"
        )

    def test_graph_with_edge_labels(self):
        assert validate_mermaid(
            "graph LR\n  A -->|yes| B\n  A -->|no| C"
        )

    def test_graph_with_decision_node(self):
        assert validate_mermaid(
            'graph TD\n  A["Start"] --> B{"n == 0?"}\n  B -- Yes --> C["Return 1"]\n  B -- No --> D["Recurse"]'
        )

    # --- flowchart (all 5 directions) ---

    def test_flowchart_td(self):
        assert validate_mermaid("flowchart TD\n  A --> B")

    def test_flowchart_lr(self):
        assert validate_mermaid("flowchart LR\n  A --> B --> C")

    def test_flowchart_tb(self):
        assert validate_mermaid("flowchart TB\n  A --> B")

    def test_flowchart_rl(self):
        assert validate_mermaid("flowchart RL\n  A --> B")

    def test_flowchart_bt(self):
        assert validate_mermaid("flowchart BT\n  A --> B")

    def test_flowchart_with_conditions(self):
        assert validate_mermaid(
            'flowchart TD\n  A[Request] --> B{Auth?}\n  B -- yes --> C[Allow]\n  B -- no --> D[Deny]'
        )

    # --- sequenceDiagram ---

    def test_sequence_diagram_basic(self):
        assert validate_mermaid(
            "sequenceDiagram\n  Alice ->> Bob: Hello\n  Bob -->> Alice: Hi"
        )

    def test_sequence_diagram_with_loop(self):
        assert validate_mermaid(
            "sequenceDiagram\n  participant User\n  participant Server\n"
            "  loop Every 5s\n    User ->> Server: ping\n  end"
        )

    def test_sequence_diagram_with_note(self):
        assert validate_mermaid(
            "sequenceDiagram\n  Alice ->> Bob: Request\n"
            "  Note right of Bob: Processing\n  Bob -->> Alice: Response"
        )

    def test_sequence_diagram_with_alt(self):
        assert validate_mermaid(
            "sequenceDiagram\n  User ->> API: login\n"
            "  alt success\n    API -->> User: token\n"
            "  else fail\n    API -->> User: 401\n  end"
        )

    # --- classDiagram ---

    def test_class_diagram_basic(self):
        assert validate_mermaid(
            "classDiagram\n  Animal <|-- Duck\n  Animal : +name str"
        )

    def test_class_diagram_with_methods(self):
        assert validate_mermaid(
            "classDiagram\n  class BankAccount{\n    +String owner\n"
            "    +deposit(amount)\n    +withdraw(amount)\n  }"
        )

    def test_class_diagram_associations(self):
        assert validate_mermaid(
            "classDiagram\n  Customer \"1\" --> \"*\" Order : places\n"
            "  Order : +id int"
        )

    # --- stateDiagram ---

    def test_state_diagram_basic(self):
        assert validate_mermaid(
            "stateDiagram\n  [*] --> Idle\n  Idle --> Active : start\n  Active --> [*]"
        )

    def test_state_diagram_v2(self):
        assert validate_mermaid(
            "stateDiagram-v2\n  [*] --> Still\n  Still --> Moving : go\n  Moving --> Still : stop"
        )

    def test_state_diagram_with_compound(self):
        assert validate_mermaid(
            "stateDiagram-v2\n  [*] --> First\n  state First {\n    [*] --> A\n    A --> B\n  }"
        )

    # --- erDiagram ---

    def test_er_diagram_basic(self):
        assert validate_mermaid(
            "erDiagram\n  CUSTOMER ||--o{ ORDER : places\n  ORDER ||--|{ LINE-ITEM : contains"
        )

    def test_er_diagram_with_attributes(self):
        assert validate_mermaid(
            "erDiagram\n  CUSTOMER {\n    string name\n    int age\n  }\n  CUSTOMER ||--o{ ORDER : places"
        )

    # --- pie ---

    def test_pie_basic(self):
        assert validate_mermaid(
            'pie\n  title Distribution\n  "A" : 40\n  "B" : 35\n  "C" : 25'
        )

    def test_pie_without_title(self):
        assert validate_mermaid('pie\n  "Cats" : 60\n  "Dogs" : 40')

    # --- mindmap ---

    def test_mindmap_basic(self):
        assert validate_mermaid(
            "mindmap\n  root((Central Idea))\n    Topic A\n      Sub 1\n    Topic B"
        )

    def test_mindmap_simple(self):
        assert validate_mermaid("mindmap\n  root\n    Branch1\n    Branch2")

    # --- timeline ---

    def test_timeline_basic(self):
        assert validate_mermaid(
            "timeline\n  title Project Timeline\n  2022 : Planning\n  2023 : Development"
        )

    def test_timeline_without_title(self):
        assert validate_mermaid("timeline\n  2020 : Event A\n  2021 : Event B")

    # --- case insensitivity ---

    def test_graph_td_uppercase(self):
        assert validate_mermaid("GRAPH TD\n  A --> B")

    def test_flowchart_mixed_case(self):
        assert validate_mermaid("FlOwChArT LR\n  A --> B")

    def test_sequence_diagram_uppercase(self):
        assert validate_mermaid("SEQUENCEDIAGRAM\n  A ->> B: hello")

    # --- semicolon separator ---

    def test_semicolon_counts_as_separator(self):
        assert validate_mermaid("graph TD;  A --> B")

    def test_semicolons_multiple(self):
        assert validate_mermaid("graph TD;  A --> B;  B --> C")


class TestValidateMermaidInvalid:
    """All scenarios that must return False."""

    # --- empty / whitespace ---

    def test_empty_string(self):
        assert not validate_mermaid("")

    def test_whitespace_only(self):
        assert not validate_mermaid("   \n  \t  ")

    def test_newlines_only(self):
        assert not validate_mermaid("\n\n\n")

    # --- header present but no content ---

    def test_graph_header_only(self):
        assert not validate_mermaid("graph TD")

    def test_flowchart_header_only(self):
        assert not validate_mermaid("flowchart LR")

    def test_sequence_header_only(self):
        assert not validate_mermaid("sequenceDiagram")

    def test_header_with_whitespace_only_content(self):
        assert not validate_mermaid("graph TD\n   \n   ")

    # --- unrecognized diagram types ---

    def test_gantt_not_recognized(self):
        # gantt is a real Mermaid type but not in the validator's allowlist
        assert not validate_mermaid("gantt\n  title A\n  section S\n    Task: 0, 1d")

    def test_gitgraph_not_recognized(self):
        assert not validate_mermaid("gitGraph\n  commit\n  branch feature")

    def test_xychart_not_recognized(self):
        assert not validate_mermaid("xychart-beta\n  title Sales\n  x-axis [Q1, Q2]")

    def test_quadrant_not_recognized(self):
        assert not validate_mermaid("quadrantChart\n  title Reach\n  x-axis Low --> High")

    def test_journey_not_recognized(self):
        assert not validate_mermaid("journey\n  title My day\n  section Morning")

    def test_block_diagram_not_recognized(self):
        assert not validate_mermaid("block-beta\n  A B C")

    # --- plain text / non-mermaid content ---

    def test_plain_sentence(self):
        assert not validate_mermaid("This is a plain text sentence.")

    def test_json_content(self):
        assert not validate_mermaid('{"key": "value", "nested": {"a": 1}}')

    def test_html_content(self):
        assert not validate_mermaid("<div>\n  <p>Hello</p>\n</div>")

    def test_sql_content(self):
        assert not validate_mermaid("SELECT * FROM users WHERE id = 1")

    def test_python_code(self):
        assert not validate_mermaid("def factorial(n):\n    if n == 0:\n        return 1")

    def test_markdown_table(self):
        assert not validate_mermaid("| Col1 | Col2 |\n|------|------|\n| A    | B    |")

    def test_single_word(self):
        assert not validate_mermaid("graph")

    def test_number_only(self):
        assert not validate_mermaid("42\n100")

    # --- fenced (not stripped at this layer) ---

    def test_fenced_mermaid_fails_without_stripping(self):
        # validate_mermaid alone doesn't strip fences — that's sanitize's job
        assert not validate_mermaid("```mermaid\ngraph TD\n  A --> B\n```")

    def test_fenced_plain_fails_without_stripping(self):
        assert not validate_mermaid("```\ngraph TD\n  A --> B\n```")


# ===========================================================================
# 4. COMBINED PIPELINE — sanitize_mermaid_labels() → validate_mermaid()
# ===========================================================================

class TestFullSanitizePipeline:
    """Mirrors exactly what the agent calls: sanitize then validate."""

    # --- all diagram types fenced → should pass ---

    @pytest.mark.parametrize("header,content", [
        ("graph TD",        "  A --> B --> C"),
        ("graph LR",        "  A --> B"),
        ("graph TB",        "  A --> B"),
        ("graph RL",        "  A --> B"),
        ("graph BT",        "  A --> B"),
        ("flowchart TD",    '  A["Start"] --> B["End"]'),
        ("flowchart LR",    "  X --> Y --> Z"),
        ("flowchart BT",    "  A --> B"),
        ("sequenceDiagram", "  User ->> Server: Request\n  Server -->> User: Response"),
        ("classDiagram",    "  Animal <|-- Dog\n  Animal : +name"),
        ("stateDiagram",    "  [*] --> Idle\n  Idle --> Active"),
        ("stateDiagram-v2", "  [*] --> Init\n  Init --> Running\n  Running --> [*]"),
        ("erDiagram",       "  CUSTOMER ||--o{ ORDER : places"),
        ("pie",             '  title Share\n  "A" : 50\n  "B" : 50'),
        ("mindmap",         "  root((Main))\n    Branch1\n    Branch2"),
        ("timeline",        "  title History\n  2020 : Start\n  2021 : Next"),
    ])
    def test_fenced_diagram_type_passes(self, header, content):
        raw = f"```mermaid\n{header}\n{content}\n```"
        assert _pipeline(raw), f"Expected pipeline to pass for: {header}"

    # --- special characters in labels survive fence stripping ---

    def test_colon_in_fenced_graph(self):
        raw = "```mermaid\ngraph TD\n  A[Step: Init] --> B[Done]\n```"
        result = sanitize_mermaid_labels(raw)
        assert validate_mermaid(result)
        assert '"Step: Init"' in result

    def test_parens_in_fenced_graph(self):
        raw = "```mermaid\ngraph TD\n  A[Result (ok)] --> B[Next]\n```"
        result = sanitize_mermaid_labels(raw)
        assert validate_mermaid(result)
        assert '"Result (ok)"' in result

    def test_multiple_specials_in_fenced_graph(self):
        raw = "```mermaid\ngraph TD\n  A[n≤10] --> B[n×2] --> C[n÷2]\n```"
        result = sanitize_mermaid_labels(raw)
        assert validate_mermaid(result)
        assert '"n≤10"' in result

    def test_already_quoted_labels_not_double_quoted(self):
        raw = '```mermaid\ngraph TD\n  A["Step: One"] --> B["Step: Two"]\n```'
        result = sanitize_mermaid_labels(raw)
        assert validate_mermaid(result)
        assert result.count('["') == 2
        assert '["["' not in result

    def test_realistic_beginner_recursion_diagram(self):
        raw = (
            "```mermaid\n"
            "graph TD\n"
            '  A["factorial(n)"] --> B{"n == 0?"}\n'
            '  B -- Yes --> C["return 1"]\n'
            '  B -- No --> D["n × factorial(n-1)"]\n'
            '  D --> A\n'
            "```"
        )
        result = sanitize_mermaid_labels(raw)
        assert validate_mermaid(result)

    def test_realistic_request_response_sequence(self):
        raw = (
            "```mermaid\n"
            "sequenceDiagram\n"
            "  participant User\n"
            "  participant API\n"
            "  participant DB\n"
            "  User ->> API: POST /login\n"
            "  API ->> DB: query credentials\n"
            "  DB -->> API: result\n"
            "  API -->> User: JWT token\n"
            "```"
        )
        assert _pipeline(raw)

    def test_realistic_class_hierarchy(self):
        raw = (
            "```mermaid\n"
            "classDiagram\n"
            "  Animal <|-- Dog\n"
            "  Animal <|-- Cat\n"
            "  Animal : +name str\n"
            "  Animal : +speak()\n"
            "  Dog : +breed str\n"
            "  Cat : +indoor bool\n"
            "```"
        )
        assert _pipeline(raw)

    def test_realistic_state_machine(self):
        raw = (
            "```mermaid\n"
            "stateDiagram-v2\n"
            "  [*] --> Idle\n"
            "  Idle --> Processing : submit\n"
            "  Processing --> Done : success\n"
            "  Processing --> Error : failure\n"
            "  Error --> Idle : retry\n"
            "  Done --> [*]\n"
            "```"
        )
        assert _pipeline(raw)

    # --- invalid body stays invalid even after fence strip ---

    def test_invalid_body_in_fence(self):
        raw = "```mermaid\nThis is not Mermaid at all.\n```"
        assert not _pipeline(raw)

    def test_empty_body_in_fence(self):
        raw = "```mermaid\n\n```"
        assert not _pipeline(raw)

    def test_unrecognized_type_in_fence(self):
        raw = "```mermaid\ngantt\n  title Plan\n  section S\n    Task: 0, 1d\n```"
        assert not _pipeline(raw)

    def test_plain_text_in_fence(self):
        raw = "```mermaid\nThe dog ran quickly.\nIt jumped over the fence.\n```"
        assert not _pipeline(raw)

    # --- plain (unfenced) diagrams still pass ---

    def test_plain_graph_td_passes(self):
        assert _pipeline("graph TD\n  A --> B")

    def test_plain_sequence_passes(self):
        assert _pipeline("sequenceDiagram\n  Alice ->> Bob: Hello")

    def test_plain_with_special_chars_sanitized_then_valid(self):
        assert _pipeline("graph TD\n  A[Step: Init] --> B[End]")


# ===========================================================================
# 5. AGENT-LEVEL RESOLVE — _resolve_diagram() via TeachingAgent
# ===========================================================================

class TestResolveDiagramViaAgent:
    """Full pipeline through the agent: streaming → extract → sanitize → validate → fallback."""

    # --- beginner: valid diagrams of various types pass through ---

    def test_beginner_fenced_graph_td(self, monkeypatch):
        out = _run_agent(monkeypatch, "```mermaid\ngraph TD\n  A[Start] --> B[End]\n```")
        assert out.status == "ok"
        assert out.content.diagram is not None
        assert out.content.diagram.startswith("graph TD")
        assert "```" not in out.content.diagram

    def test_beginner_fenced_graph_lr(self, monkeypatch):
        out = _run_agent(monkeypatch, "```mermaid\ngraph LR\n  A --> B --> C\n```")
        assert out.status == "ok"
        assert out.content.diagram.startswith("graph LR")

    def test_beginner_fenced_flowchart(self, monkeypatch):
        out = _run_agent(monkeypatch, "```mermaid\nflowchart TD\n  A --> B --> C\n```")
        assert out.status == "ok"
        assert out.content.diagram.startswith("flowchart TD")

    def test_beginner_fenced_sequence_diagram(self, monkeypatch):
        out = _run_agent(
            monkeypatch,
            "```mermaid\nsequenceDiagram\n  User ->> API: Call\n  API -->> User: Response\n```",
        )
        assert out.status == "ok"
        assert out.content.diagram.startswith("sequenceDiagram")

    def test_beginner_plain_graph_td(self, monkeypatch):
        out = _run_agent(monkeypatch, "graph TD\n  A --> B\n  B --> C")
        assert out.status == "ok"
        assert out.content.diagram.startswith("graph TD")

    def test_beginner_fenced_statediagram(self, monkeypatch):
        out = _run_agent(
            monkeypatch,
            "```mermaid\nstateDiagram-v2\n  [*] --> Idle\n  Idle --> Active\n  Active --> [*]\n```",
        )
        assert out.status == "ok"
        assert out.content.diagram.startswith("stateDiagram-v2")

    def test_beginner_fenced_class_diagram(self, monkeypatch):
        out = _run_agent(
            monkeypatch,
            "```mermaid\nclassDiagram\n  Animal <|-- Dog\n  Animal : +name\n```",
        )
        assert out.status == "ok"
        assert out.content.diagram.startswith("classDiagram")

    def test_beginner_fenced_er_diagram(self, monkeypatch):
        out = _run_agent(
            monkeypatch,
            "```mermaid\nerDiagram\n  CUSTOMER ||--o{ ORDER : places\n```",
        )
        assert out.status == "ok"
        assert out.content.diagram.startswith("erDiagram")

    # --- beginner: special chars sanitized in stored diagram ---

    def test_beginner_special_chars_quoted_in_output(self, monkeypatch):
        out = _run_agent(
            monkeypatch,
            "```mermaid\ngraph TD\n  A[Step: Init] --> B[Result (ok)]\n```",
        )
        assert out.status == "ok"
        assert '"Step: Init"' in out.content.diagram
        assert '"Result (ok)"' in out.content.diagram

    # --- beginner: invalid diagram → retry → success ---

    def test_beginner_retry_succeeds(self, monkeypatch):
        """Initial streaming gives invalid Mermaid; retry returns valid full markdown."""
        valid_retry = (
            "**Explanation**\nRetry explanation.\n\n"
            "**Diagram**\ngraph TD\n  A --> B\n\n"
            "**Notes**\nRetry notes.\n\n"
            "**Example**\nRetry example."
        )
        out = _run_agent(
            monkeypatch,
            "NOT VALID MERMAID AT ALL",
            retry_response=valid_retry,
        )
        assert out.status == "ok"
        assert out.content.diagram is not None
        assert out.content.diagram.startswith("graph TD")

    def test_beginner_retry_also_invalid_returns_none(self, monkeypatch):
        """Both initial and retry return garbage → diagram is None (not a placeholder)."""
        bad_retry = (
            "**Explanation**\nExplanation.\n\n"
            "**Diagram**\nSTILL NOT VALID\n\n"
            "**Notes**\nNotes.\n\n"
            "**Example**\nExample."
        )
        out = _run_agent(
            monkeypatch,
            "NOT VALID MERMAID",
            retry_response=bad_retry,
        )
        assert out.status == "ok"
        assert out.content.diagram is None

    def test_beginner_no_diagram_section_retries_then_none(self, monkeypatch):
        """LLM omits **Diagram** section entirely for beginner → retry → None."""
        no_diagram_md = (
            "**Explanation**\nExplanation.\n\n"
            "**Notes**\nNotes.\n\n"
            "**Example**\nExample."
        )
        bad_retry = (
            "**Explanation**\nExplanation.\n\n"
            "**Diagram**\nBAD\n\n"
            "**Notes**\nNotes.\n\n"
            "**Example**\nExample."
        )
        out = _run_agent(monkeypatch, "", retry_response=bad_retry)
        # Empty diagram body → initial invalid → retry returns bad → None
        assert out.status == "ok"
        assert out.content.diagram is None

    # --- intermediate: invalid or absent → None immediately, no retry ---

    def test_intermediate_invalid_diagram_returns_none(self, monkeypatch):
        out = _run_agent(monkeypatch, "NOT VALID MERMAID", mode="intermediate")
        assert out.status == "ok"
        assert out.content.diagram is None

    def test_intermediate_valid_diagram_passes_through(self, monkeypatch):
        out = _run_agent(
            monkeypatch,
            "```mermaid\ngraph LR\n  A --> B --> C\n```",
            mode="intermediate",
        )
        assert out.status == "ok"
        assert out.content.diagram is not None
        assert out.content.diagram.startswith("graph LR")

    def test_intermediate_no_diagram_section_returns_none(self, monkeypatch):
        """**Diagram** section absent for intermediate → None."""
        monkeypatch.setenv("TEACHING_MODEL", "fake/model")
        monkeypatch.setattr(
            "teaching_agent.guardrail.call_llm",
            lambda msgs, cfg: ('{"category": "valid_question", "reason": "ok"}', 0),
        )
        monkeypatch.setattr(
            "teaching_agent.agent.call_llm_stream",
            lambda msgs, cfg: iter([(ch, 0) for ch in (
                "**Explanation**\nExplanation.\n\n"
                "**Notes**\nNotes.\n\n"
                "**Example**\nExample."
            )]),
        )
        monkeypatch.setattr(
            "teaching_agent.agent.get_max_reflection_iterations", lambda m: 0
        )
        out, _ = agent_module.TeachingAgent().run(
            {"topic": "Sorting", "output_mode": "intermediate"}, _noop
        )
        assert out.status == "ok"
        assert out.content.diagram is None

    # --- advanced: valid only if LLM provides a valid diagram ---

    def test_advanced_valid_diagram_passes(self, monkeypatch):
        out = _run_agent(
            monkeypatch,
            "```mermaid\nflowchart LR\n  A --> B --> C\n```",
            mode="advanced",
        )
        assert out.status == "ok"
        assert out.content.diagram.startswith("flowchart LR")

    def test_advanced_invalid_diagram_returns_none(self, monkeypatch):
        out = _run_agent(monkeypatch, "some random text", mode="advanced")
        assert out.status == "ok"
        assert out.content.diagram is None

    # --- confirm no generic placeholder ever appears ---

    def test_no_generic_placeholder_on_failure(self, monkeypatch):
        """The old 'A[Concept] --> B[Key Idea] --> C[Result]' must never be returned."""
        bad_retry = (
            "**Explanation**\nExplanation.\n\n"
            "**Diagram**\nJUNK\n\n"
            "**Notes**\nNotes.\n\n"
            "**Example**\nExample."
        )
        out = _run_agent(monkeypatch, "JUNK", retry_response=bad_retry)
        assert out.content.diagram is None
        # Belt-and-suspenders: the old fallback string must not appear
        assert out.content.diagram != "graph TD\n  A[Concept] --> B[Key Idea] --> C[Result]"
