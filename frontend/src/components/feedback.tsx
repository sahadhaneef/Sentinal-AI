import { createContext, useContext, useState, type ReactNode } from 'react';
const Feedback = createContext<(message: string) => void>(() => {});
export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('');
  return (
    <Feedback.Provider value={setMessage}>
      {children}
      <div className="toast" role="status" aria-live="polite">
        {message && (
          <>
            <span>{message}</span>
            <button onClick={() => setMessage('')} aria-label="Dismiss notification">
              ×
            </button>
          </>
        )}
      </div>
    </Feedback.Provider>
  );
}
export const useNotify = () => useContext(Feedback);
