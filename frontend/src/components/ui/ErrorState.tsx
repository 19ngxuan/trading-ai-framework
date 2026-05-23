import { ApiError } from "../../api/client";

type ErrorStateProps = {
  error: unknown;
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return `${error.errorCode}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong.";
}

export function ErrorState({ error }: ErrorStateProps) {
  return <div className="state-box state-box-error">{errorMessage(error)}</div>;
}
