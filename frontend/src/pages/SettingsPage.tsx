import { useQuery } from "@tanstack/react-query";

import { getHealth } from "../api/healthApi";

export function SettingsPage() {
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
  });

  return (
    <section className="panel">
      <p className="eyebrow">System</p>
      <h2>Settings</h2>
      <dl className="status-list">
        <div>
          <dt>Backend</dt>
          <dd>
            {healthQuery.isLoading && "Checking..."}
            {healthQuery.isError && "Unavailable"}
            {healthQuery.data &&
              `${healthQuery.data.status} (${healthQuery.data.version})`}
          </dd>
        </div>
      </dl>
    </section>
  );
}
