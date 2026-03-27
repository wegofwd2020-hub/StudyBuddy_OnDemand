import { describe, it, expect } from "vitest";

// Test the quiz reducer logic in isolation (extracted for unit testing)
type Phase = "answering" | "reviewing" | "scoring";
interface State {
  phase: Phase;
  questionIndex: number;
  selectedIndex: number | null;
  correctCount: number;
}
type Action =
  | { type: "SELECT"; index: number }
  | { type: "REVIEWED"; correct: boolean }
  | { type: "NEXT" }
  | { type: "SCORE" };

function quizReducer(state: State, action: Action): State {
  switch (action.type) {
    case "SELECT":
      return { ...state, selectedIndex: action.index };
    case "REVIEWED":
      return {
        ...state,
        phase: "reviewing",
        correctCount: action.correct ? state.correctCount + 1 : state.correctCount,
      };
    case "NEXT":
      return {
        ...state,
        phase: "answering",
        questionIndex: state.questionIndex + 1,
        selectedIndex: null,
      };
    case "SCORE":
      return { ...state, phase: "scoring" };
    default:
      return state;
  }
}

const INITIAL: State = {
  phase: "answering",
  questionIndex: 0,
  selectedIndex: null,
  correctCount: 0,
};

describe("quiz state machine", () => {
  it("starts in answering phase", () => {
    expect(INITIAL.phase).toBe("answering");
  });

  it("SELECT sets selectedIndex", () => {
    const s = quizReducer(INITIAL, { type: "SELECT", index: 2 });
    expect(s.selectedIndex).toBe(2);
  });

  it("REVIEWED transitions to reviewing", () => {
    const s = quizReducer(INITIAL, { type: "REVIEWED", correct: false });
    expect(s.phase).toBe("reviewing");
  });

  it("REVIEWED increments correctCount when correct", () => {
    const s = quizReducer(INITIAL, { type: "REVIEWED", correct: true });
    expect(s.correctCount).toBe(1);
  });

  it("REVIEWED does not increment correctCount when wrong", () => {
    const s = quizReducer(INITIAL, { type: "REVIEWED", correct: false });
    expect(s.correctCount).toBe(0);
  });

  it("NEXT advances question index and resets selection", () => {
    const reviewing: State = { ...INITIAL, phase: "reviewing", selectedIndex: 1 };
    const s = quizReducer(reviewing, { type: "NEXT" });
    expect(s.questionIndex).toBe(1);
    expect(s.selectedIndex).toBeNull();
    expect(s.phase).toBe("answering");
  });

  it("SCORE transitions to scoring", () => {
    const s = quizReducer(INITIAL, { type: "SCORE" });
    expect(s.phase).toBe("scoring");
  });

  it("full 3-question flow accumulates correct count", () => {
    let s = INITIAL;
    // Q1 correct
    s = quizReducer(s, { type: "SELECT", index: 0 });
    s = quizReducer(s, { type: "REVIEWED", correct: true });
    s = quizReducer(s, { type: "NEXT" });
    // Q2 wrong
    s = quizReducer(s, { type: "SELECT", index: 1 });
    s = quizReducer(s, { type: "REVIEWED", correct: false });
    s = quizReducer(s, { type: "NEXT" });
    // Q3 correct
    s = quizReducer(s, { type: "SELECT", index: 2 });
    s = quizReducer(s, { type: "REVIEWED", correct: true });
    s = quizReducer(s, { type: "SCORE" });

    expect(s.correctCount).toBe(2);
    expect(s.phase).toBe("scoring");
    expect(s.questionIndex).toBe(2);
  });
});
