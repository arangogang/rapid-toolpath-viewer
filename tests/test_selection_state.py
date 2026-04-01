"""Tests for SelectionState model -- observable multi-select state.

Covers: SEL-01, SEL-02
"""

from rapid_viewer.ui.selection_state import SelectionState


class TestSelectionState:
    """Unit tests for SelectionState model."""

    def test_initial_empty(self, qtbot):
        """New SelectionState has empty selected_indices."""
        state = SelectionState()
        assert state.selected_indices == frozenset()

    def test_select_single(self, qtbot):
        """select_single(3) sets selected_indices to frozenset({3}) and emits signal."""
        state = SelectionState()
        received = []
        state.selection_changed.connect(lambda s: received.append(s))

        state.select_single(3)

        assert state.selected_indices == frozenset({3})
        assert received == [frozenset({3})]

    def test_select_single_replaces(self, qtbot):
        """select_single(5) after select_single(3) replaces selection."""
        state = SelectionState()
        state.select_single(3)

        received = []
        state.selection_changed.connect(lambda s: received.append(s))

        state.select_single(5)

        assert state.selected_indices == frozenset({5})
        assert received == [frozenset({5})]

    def test_toggle_add(self, qtbot):
        """toggle(2) on empty selection adds 2."""
        state = SelectionState()
        received = []
        state.selection_changed.connect(lambda s: received.append(s))

        state.toggle(2)

        assert state.selected_indices == frozenset({2})
        assert received == [frozenset({2})]

    def test_toggle_remove(self, qtbot):
        """toggle(2) when 2 is selected removes it."""
        state = SelectionState()
        state.toggle(2)

        received = []
        state.selection_changed.connect(lambda s: received.append(s))

        state.toggle(2)

        assert state.selected_indices == frozenset()
        assert received == [frozenset()]

    def test_toggle_multi(self, qtbot):
        """toggle(1) then toggle(3) results in frozenset({1, 3})."""
        state = SelectionState()
        state.toggle(1)
        state.toggle(3)

        assert state.selected_indices == frozenset({1, 3})

    def test_clear(self, qtbot):
        """clear() empties selection and emits selection_changed with frozenset()."""
        state = SelectionState()
        state.select_single(5)
        state.toggle(7)

        received = []
        state.selection_changed.connect(lambda s: received.append(s))

        state.clear()

        assert state.selected_indices == frozenset()
        assert received == [frozenset()]

    def test_extend_to(self, qtbot):
        """extend_to(idx) behaves like toggle (Ctrl+click per D-02)."""
        state = SelectionState()
        state.select_single(1)

        received = []
        state.selection_changed.connect(lambda s: received.append(s))

        state.extend_to(3)

        assert state.selected_indices == frozenset({1, 3})
        assert received == [frozenset({1, 3})]
