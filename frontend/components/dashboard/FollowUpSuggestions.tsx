'use client';

/** Plain follow-up row — matches assistant body typography, no boxes. */
export const FOLLOW_UP_SUGGESTION_ROW_CLASS =
  'block w-full max-w-full cursor-pointer py-1 text-left text-[15px] font-normal leading-7 text-zinc-800 transition duration-150 hover:text-zinc-950 hover:underline hover:underline-offset-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-300 focus-visible:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-60';

type FollowUpSuggestionsProps = {
  questions: string[];
  onSelect: (question: string) => void;
  disabled?: boolean;
};

export function FollowUpSuggestions({
  questions,
  onSelect,
  disabled = false,
}: FollowUpSuggestionsProps) {
  if (questions.length === 0) {
    return null;
  }

  return (
    <div className="mt-5 space-y-2.5" data-testid="follow-up-suggestions">
      <p
        className="text-[13px] font-semibold uppercase tracking-[0.12em] text-indigo-600"
        data-testid="follow-up-heading"
      >
        You May Also Be Interested In
      </p>
      <ul className="flex max-w-full flex-col gap-1.5">
        {questions.map((question, index) => (
          <li key={`${index}-${question}`}>
            <button
              type="button"
              disabled={disabled}
              data-testid="follow-up-suggestion"
              data-suggestion-index={index}
              onClick={() => onSelect(question)}
              className={FOLLOW_UP_SUGGESTION_ROW_CLASS}
            >
              {question}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
