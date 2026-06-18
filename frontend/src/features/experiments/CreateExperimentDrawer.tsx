import { useEffect } from "react";

import { CreateExperimentForm } from "./CreateExperimentForm";

type CreateExperimentDrawerProps = {
  isOpen: boolean;
  onClose: () => void;
};

export function CreateExperimentDrawer({
  isOpen,
  onClose,
}: CreateExperimentDrawerProps) {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      aria-labelledby="create-experiment-drawer-title"
      aria-modal="true"
      className="drawer-overlay"
      role="dialog"
    >
      <button
        aria-label="Close create experiment panel"
        className="drawer-backdrop"
        onClick={onClose}
        type="button"
      />
      <aside className="drawer-panel">
        <div className="drawer-header">
          <div>
            <p className="eyebrow">Create</p>
            <h2 id="create-experiment-drawer-title">New Experiment</h2>
          </div>
          <button onClick={onClose} type="button">
            Close
          </button>
        </div>
        <CreateExperimentForm onCancel={onClose} />
      </aside>
    </div>
  );
}
