import { FormEvent, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../components/ui/ErrorState";
import { LoadingState } from "../../components/ui/LoadingState";
import type {
  AgentMode,
  CreateExperimentPayload,
  ExperimentMode,
  FeeModelType,
  StrategyType,
  TradingFrequency,
} from "../../types/experiment";
import { useCreateExperiment, useOptions } from "./hooks";

type FormState = {
  name: string;
  mode: ExperimentMode;
  strategyType: StrategyType;
  assetSymbol: string;
  initialCapital: string;
  startDate: string;
  endDate: string;
  tradingFrequency: TradingFrequency;
  feeModelType: FeeModelType;
  feeValue: string;
  movingAverageWindow: string;
  agentMode: AgentMode | "";
  modelName: string;
  confidenceThreshold: string;
  fallbackAction: "HOLD";
};

type CreateExperimentFormProps = {
  onCancel?: () => void;
};

const initialState: FormState = {
  name: "",
  mode: "HISTORICAL_SIMULATION",
  strategyType: "BUY_AND_HOLD",
  assetSymbol: "SPY",
  initialCapital: "10000",
  startDate: "2024-01-02",
  endDate: "2024-01-05",
  tradingFrequency: "DAILY",
  feeModelType: "NONE",
  feeValue: "0",
  movingAverageWindow: "",
  agentMode: "",
  modelName: "",
  confidenceThreshold: "",
  fallbackAction: "HOLD",
};

const STRATEGY_DESCRIPTIONS: Record<StrategyType, string> = {
  BUY_AND_HOLD: "Buy once, then hold the SPY position.",
  MOVING_AVERAGE: "Use a daily moving average signal.",
  AGENTIC_AI: "Use a controlled agent decision producer.",
  OPENING_RANGE_BREAKOUT: "Use 5-minute opening range breakout rules.",
  PAPER_TRADING_SMOKE_TEST: "Run 1-share paper diagnostics only.",
};

const MODE_DESCRIPTIONS: Record<ExperimentMode, string> = {
  HISTORICAL_SIMULATION: "Backtest over a fixed date range.",
  PAPER_TRADING: "Run against Alpaca paper trading when scheduled or stepped.",
};

function formatEnumLabel(value: string) {
  return value.replace(/_/g, " ");
}

function defaultFrequencyFor(strategyType: StrategyType): TradingFrequency {
  if (strategyType === "OPENING_RANGE_BREAKOUT") return "INTRADAY_5_MIN";
  if (strategyType === "PAPER_TRADING_SMOKE_TEST") return "TEST_1_MIN";
  return "DAILY";
}

function frequenciesFor(
  strategyType: StrategyType,
  frequencies: TradingFrequency[],
) {
  const defaultFrequency = defaultFrequencyFor(strategyType);
  return frequencies.filter((frequency) => frequency === defaultFrequency);
}

function validate(state: FormState): string | null {
  if (!state.name.trim()) return "Name is required.";
  const initialCapital = Number(state.initialCapital);
  if (!Number.isFinite(initialCapital) || initialCapital <= 0) {
    return "Initial capital must be positive.";
  }
  if (state.mode === "HISTORICAL_SIMULATION" && state.startDate > state.endDate) {
    return "Start date must be before or equal to end date.";
  }
  const feeValue = Number(state.feeValue);
  if (!Number.isFinite(feeValue) || feeValue < 0) {
    return "Fee value must be greater than or equal to 0.";
  }
  if (state.movingAverageWindow) {
    const window = Number(state.movingAverageWindow);
    if (!Number.isInteger(window) || window <= 0) {
      return "Moving average window must be a positive integer.";
    }
  }
  if (state.confidenceThreshold) {
    const threshold = Number(state.confidenceThreshold);
    if (!Number.isFinite(threshold) || threshold < 0 || threshold > 1) {
      return "Confidence threshold must be between 0 and 1.";
    }
  }
  if (state.strategyType === "AGENTIC_AI" && state.mode === "PAPER_TRADING") {
    if (state.agentMode && state.agentMode !== "SINGLE_AGENT") {
      return "Paper trading Agentic AI supports SINGLE_AGENT mode only.";
    }
    if (!state.modelName.trim()) {
      return "Paper trading Agentic AI requires a model selection.";
    }
    if (state.tradingFrequency !== "DAILY") {
      return "Paper trading Agentic AI supports DAILY frequency only.";
    }
  }
  return null;
}

export function CreateExperimentForm({ onCancel }: CreateExperimentFormProps) {
  const navigate = useNavigate();
  const optionsQuery = useOptions();
  const createMutation = useCreateExperiment();
  const [state, setState] = useState<FormState>(initialState);
  const [validationError, setValidationError] = useState<string | null>(null);
  const isHistorical = state.mode === "HISTORICAL_SIMULATION";
  const isPaper = state.mode === "PAPER_TRADING";
  const hasStrategyFields =
    state.strategyType === "MOVING_AVERAGE" || state.strategyType === "AGENTIC_AI";
  const availableFrequencies = frequenciesFor(
    state.strategyType,
    optionsQuery.data?.tradingFrequencies ?? [],
  );

  const riskConfig = useMemo(
    () => ({
      maxPositionSizePct: 1,
      maxTradesPerDay: null,
      maxTradesPerWeek: null,
      maxDrawdownPct: null,
      drawdownAction: "BLOCK_TRADES",
      fallbackAction: state.fallbackAction,
    }),
    [state.fallbackAction],
  );

  if (optionsQuery.isLoading) {
    return <LoadingState label="Loading options..." />;
  }

  if (optionsQuery.isError || !optionsQuery.data) {
    return (
      <div className="state-box state-box-error">
        {optionsQuery.error
          ? errorMessage(optionsQuery.error)
          : "Unable to load experiment options."}
      </div>
    );
  }

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setState((current) => ({ ...current, [key]: value }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const error = validate(state);
    setValidationError(error);
    if (error) return;

    const payload: CreateExperimentPayload = {
      name: state.name.trim(),
      mode: state.mode,
      strategyType: state.strategyType,
      assetSymbol: state.assetSymbol,
      initialCapital: Number(state.initialCapital),
      startDate: state.startDate,
      endDate: state.endDate,
      tradingFrequency: state.tradingFrequency,
      feeModelType: state.feeModelType,
      feeValue: Number(state.feeValue),
      strategyConfig: {
        movingAverageWindow: state.movingAverageWindow
          ? Number(state.movingAverageWindow)
          : null,
        agentMode: state.agentMode || null,
        modelName: state.modelName || null,
        confidenceThreshold: state.confidenceThreshold
          ? Number(state.confidenceThreshold)
          : null,
        parametersJson: { riskConfig },
      },
    };

    try {
      const response = await createMutation.mutateAsync(payload);
      navigate(`/experiments/${response.experiment.id}`);
    } catch {
      // Error rendered below from mutation state.
    }
  };

  return (
    <form className="create-experiment-form" onSubmit={(event) => void submit(event)}>
      <div className="create-summary">
        <div>
          <span className="summary-label">Mode</span>
          <strong>{formatEnumLabel(state.mode)}</strong>
        </div>
        <div>
          <span className="summary-label">Strategy</span>
          <strong>{formatEnumLabel(state.strategyType)}</strong>
        </div>
        <div>
          <span className="summary-label">Asset</span>
          <strong>{state.assetSymbol}</strong>
        </div>
      </div>

      <section className="form-section form-card">
        <div className="form-section-heading">
          <span className="step-pill">01</span>
          <div>
            <h3>Experiment Setup</h3>
            <p>Name the run and choose the execution mode.</p>
          </div>
        </div>
        <label>
          Name
          <input
            value={state.name}
            onChange={(event) => update("name", event.target.value)}
            required
          />
        </label>
        <label>
          Mode
          <select
            value={state.mode}
            onChange={(event) => {
              const nextMode = event.target.value as ExperimentMode;
              setState((current) => ({
                ...current,
                mode: nextMode,
                tradingFrequency:
                  nextMode === "PAPER_TRADING"
                    ? defaultFrequencyFor(current.strategyType)
                    : current.tradingFrequency,
                agentMode:
                  nextMode === "PAPER_TRADING"
                    && current.strategyType === "AGENTIC_AI"
                    ? "SINGLE_AGENT"
                    : current.agentMode,
                modelName:
                  nextMode === "PAPER_TRADING"
                    && current.strategyType === "AGENTIC_AI"
                    ? optionsQuery.data.scadsaiDefaultModel
                    : current.modelName,
              }));
            }}
          >
            {optionsQuery.data.modes.map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </select>
          <small>{MODE_DESCRIPTIONS[state.mode]}</small>
        </label>
        <label>
          Strategy
          <select
            value={state.strategyType}
            onChange={(event) => {
              const nextStrategy = event.target.value as StrategyType;
              setState((current) => ({
                ...current,
                strategyType: nextStrategy,
                movingAverageWindow:
                  nextStrategy === "MOVING_AVERAGE" ? "3" : "",
                tradingFrequency: defaultFrequencyFor(nextStrategy),
                mode:
                  nextStrategy === "PAPER_TRADING_SMOKE_TEST"
                    ? "PAPER_TRADING"
                    : current.mode,
                agentMode:
                  nextStrategy === "AGENTIC_AI" && current.mode === "PAPER_TRADING"
                    ? "SINGLE_AGENT"
                    : current.agentMode,
                modelName:
                  nextStrategy === "AGENTIC_AI" && current.mode === "PAPER_TRADING"
                    ? optionsQuery.data.scadsaiDefaultModel
                    : current.modelName,
              }));
            }}
          >
            {optionsQuery.data.strategies.map((strategy) => (
              <option key={strategy} value={strategy}>
                {strategy}
              </option>
            ))}
          </select>
          <small>{STRATEGY_DESCRIPTIONS[state.strategyType]}</small>
        </label>
        {state.strategyType === "PAPER_TRADING_SMOKE_TEST" && (
          <div className="state-box">
            Smoke-test strategy creates alternating 1-share Alpaca paper BUY/SELL
            orders for operational testing only. It is not an investment strategy.
          </div>
        )}
        <label>
          Asset
          <select
            value={state.assetSymbol}
            onChange={(event) => update("assetSymbol", event.target.value)}
          >
            {optionsQuery.data.assets.map((asset) => (
              <option key={asset} value={asset}>
                {asset}
              </option>
            ))}
          </select>
        </label>
        <label>
          Initial Capital
          <input
            min="0"
            step="0.01"
            type="number"
            value={state.initialCapital}
            onChange={(event) => update("initialCapital", event.target.value)}
            required
          />
        </label>
      </section>

      <section className="form-section form-card">
        <div className="form-section-heading">
          <span className="step-pill">02</span>
          <div>
            <h3>Execution Context</h3>
            <p>
              {isHistorical
                ? "Historical simulations need a bounded data window."
                : "Paper trading uses live scheduler context; dates are not required here."}
            </p>
          </div>
        </div>
        {isHistorical ? (
          <div className="field-pair">
            <label>
              Start Date
              <input
                type="date"
                value={state.startDate}
                onChange={(event) => update("startDate", event.target.value)}
                required
              />
            </label>
            <label>
              End Date
              <input
                type="date"
                value={state.endDate}
                onChange={(event) => update("endDate", event.target.value)}
                required
              />
            </label>
          </div>
        ) : (
          <div className="context-note">
            Paper experiments are controlled by lifecycle actions and the paper
            scheduler. Historical start/end dates are not part of the user flow.
          </div>
        )}
        <label>
          Frequency
          <select
            value={state.tradingFrequency}
            onChange={(event) =>
              update("tradingFrequency", event.target.value as TradingFrequency)
            }
          >
            {availableFrequencies.map((frequency) => (
              <option key={frequency} value={frequency}>
                {frequency}
              </option>
            ))}
          </select>
          {isPaper && state.strategyType === "OPENING_RANGE_BREAKOUT" && (
            <small>ORB paper trading evaluates completed 5-minute bars.</small>
          )}
        </label>
      </section>

      <section className="form-section form-card">
        <div className="form-section-heading">
          <span className="step-pill">03</span>
          <div>
            <h3>Strategy Details</h3>
            <p>
              {hasStrategyFields
                ? "Only fields required by the selected strategy are shown."
                : "This strategy does not need additional inputs."}
            </p>
          </div>
        </div>
        {state.strategyType === "MOVING_AVERAGE" && (
          <label>
            Moving Average Window
            <input
              min="1"
              step="1"
              type="number"
              value={state.movingAverageWindow}
              onChange={(event) =>
                update("movingAverageWindow", event.target.value)
              }
            />
          </label>
        )}
        {state.strategyType === "AGENTIC_AI" && (
          <>
            <label>
              Agent Mode
              <select
                value={state.agentMode}
                onChange={(event) =>
                  update("agentMode", event.target.value as AgentMode | "")
                }
              >
                <option value="">None</option>
                {optionsQuery.data.agentModes
                  .filter((mode) =>
                    state.mode === "PAPER_TRADING" ? mode === "SINGLE_AGENT" : true,
                  )
                  .map((mode) => (
                  <option key={mode} value={mode}>
                    {mode}
                  </option>
                  ))}
              </select>
            </label>
            {state.mode === "PAPER_TRADING" ? (
              <label>
                ScaDS.AI Model
                <select
                  value={state.modelName || optionsQuery.data.scadsaiDefaultModel}
                  onChange={(event) => update("modelName", event.target.value)}
                >
                  {optionsQuery.data.scadsaiAllowedModels.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label>
                Model Name
                <input
                  value={state.modelName}
                  onChange={(event) => update("modelName", event.target.value)}
                />
              </label>
            )}
            <label>
              Confidence Threshold
              <input
                min="0"
                max="1"
                step="0.01"
                type="number"
                value={state.confidenceThreshold}
                onChange={(event) =>
                  update("confidenceThreshold", event.target.value)
                }
              />
            </label>
          </>
        )}
        {!hasStrategyFields && (
          <div className="context-note">
            The selected strategy is fully defined by mode, asset, frequency,
            and the backend risk rules.
          </div>
        )}
      </section>

      <section className="form-section form-card form-card-muted">
        <div className="form-section-heading">
          <span className="step-pill">04</span>
          <div>
            <h3>Fees and Risk Defaults</h3>
            <p>These defaults keep execution conservative unless backend rules change.</p>
          </div>
        </div>
        <label>
          Fallback Action
          <input value={state.fallbackAction} readOnly />
        </label>
        <label>
          Fee Model
          <select
            value={state.feeModelType}
            onChange={(event) =>
              update("feeModelType", event.target.value as FeeModelType)
            }
          >
            {optionsQuery.data.feeModelTypes.map((feeModel) => (
              <option key={feeModel} value={feeModel}>
                {feeModel}
              </option>
            ))}
          </select>
        </label>
        <label>
          Fee Value
          <input
            min="0"
            step="0.0001"
            type="number"
            value={state.feeValue}
            onChange={(event) => update("feeValue", event.target.value)}
          />
        </label>
      </section>

      {(validationError || createMutation.error) && (
        <div className="state-box state-box-error">
          {validationError || errorMessage(createMutation.error)}
        </div>
      )}

      <div className="drawer-form-footer">
        <button
          type="button"
          onClick={() => {
            if (onCancel) {
              onCancel();
              return;
            }
            navigate("/experiments");
          }}
        >
          Cancel
        </button>
        <button
          className="button-primary"
          disabled={createMutation.isPending}
          type="submit"
        >
          Create Experiment
        </button>
      </div>
    </form>
  );
}
