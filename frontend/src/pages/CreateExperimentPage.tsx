import { CreateExperimentForm } from "../features/experiments/CreateExperimentForm";

export function CreateExperimentPage() {
  return (
    <div className="page-stack">
      <div>
        <p className="eyebrow">Create</p>
        <h2>New Experiment</h2>
      </div>
      <section className="panel wide-panel">
        <CreateExperimentForm />
      </section>
    </div>
  );
}
