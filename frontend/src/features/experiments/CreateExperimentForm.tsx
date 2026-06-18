import { FormEvent, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../components/ui/ErrorState";
import { LoadingState } from "../../components/ui/LoadingState";
import type {
  AgentMode,
  CreateExperimentPayload,
  ExperimentMode,
  FeeModelType,
  PositionSizingType,
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
  strategyVersion: string;
  movingAverageWindow: string;
  positionSizingType: PositionSizingType;
  positionSizingValue: string;
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
  strategyVersion: "buy-and-hold-v1",
  movingAverageWindow: "",
  positionSizingType: "ALL_IN",
  positionSizingValue: "",
  agentMode: "",
  modelName: "",
  confidenceThreshold: "",
  fallbackAction: "HOLD",
};

function strategyVersion(strategyType: StrategyType) {
  if (strategyType === "MOVING_AVERAGE") return "moving-average-v1";
  if (strategyType === "AGENTIC_AI") return "agentic-ai-v1";
  if (strategyType === "OPENING_RANGE_BREAKOUT") {
    return "opening-range-breakout-v1";
  }
  if (strategyType === "PAPER_TRADING_SMOKE_TEST") {
    return "paper-trading-smoke-test-v1";
  }
  return "buy-and-hold-v1";
}

function validate(state: FormState): string | null {
  if (!state.name.trim()) return "Name is required.";
  if (!state.strategyVersion.trim()) return "Strategy version is required.";
  const initialCapital = Number(state.initialCapital);
  if (!Number.isFinite(initialCapital) || initialCapital <= 0) {
    return "Initial capital must be positive.";
  }
  if (state.startDate > state.endDate) {
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
  if (state.positionSizingType !== "ALL_IN") {
    const sizingValue = Number(state.positionSizingValue);
    if (!Number.isFinite(sizingValue)) {
      return "Position sizing value is required.";
    }
    if (state.positionSizingType === "FIXED_CASH" && sizingValue <= 0) {
      return "Fixed cash position sizing must be positive.";
    }
    if (
      state.positionSizingType === "PERCENT_OF_PORTFOLIO" &&
      (sizingValue <= 0 || sizingValue > 1)
    ) {
      return "Percent of portfolio must be greater than 0 and less than or equal to 1.";
    }
    if (
      state.positionSizingType === "FIXED_QUANTITY" &&
      (!Number.isInteger(sizingValue) || sizingValue <= 0)
    ) {
      return "Fixed quantity must be a positive whole number.";
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
        strategyVersion: state.strategyVersion.trim(),
        movingAverageWindow: state.movingAverageWindow
          ? Number(state.movingAverageWindow)
          : null,
        positionSizingType: state.positionSizingType || null,
        positionSizingValue:
          state.positionSizingType === "ALL_IN"
            ? null
            : Number(state.positionSizingValue),
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
    <form className="form-grid" onSubmit={(event) => void submit(event)}>
      <section className="form-section">
        <h3>Basic Configuration</h3>
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
                tradingFrequency:
                  nextMode === "PAPER_TRADING"
                    && current.strategyType === "AGENTIC_AI"
                    ? "DAILY"
                    : current.tradingFrequency,
              }));
            }}
          >
            {optionsQuery.data.modes.map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </select>
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
                strategyVersion: strategyVersion(nextStrategy),
                movingAverageWindow:
                  nextStrategy === "MOVING_AVERAGE" ? "3" : "",
                tradingFrequency:
                  nextStrategy === "OPENING_RANGE_BREAKOUT"
                    ? "INTRADAY_5_MIN"
                    : nextStrategy === "PAPER_TRADING_SMOKE_TEST"
                      ? "TEST_1_MIN"
                    : current.tradingFrequency === "INTRADAY_5_MIN"
                        || current.tradingFrequency === "TEST_1_MIN"
                      ? "DAILY"
                      : current.tradingFrequency,
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
                positionSizingType:
                  nextStrategy === "PAPER_TRADING_SMOKE_TEST"
                    ? "FIXED_QUANTITY"
                    : current.positionSizingType,
                positionSizingValue:
                  nextStrategy === "PAPER_TRADING_SMOKE_TEST"
                    ? "1"
                    : current.positionSizingValue,
              }));
            }}
          >
            {optionsQuery.data.strategies.map((strategy) => (
              <option key={strategy} value={strategy}>
                {strategy}
              </option>
            ))}
          </select>
        </label>
        {state.strategyType === "PAPER_TRADING_SMOKE_TEST" && (
          <div className="state-box full-span">
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
        <label>
          Frequency
          <select
            value={state.tradingFrequency}
            onChange={(event) =>
              update("tradingFrequency", event.target.value as TradingFrequency)
            }
          >
            {optionsQuery.data.tradingFrequencies.map((frequency) => (
              <option key={frequency} value={frequency}>
                {frequency}
              </option>
            ))}
          </select>
        </label>
      </section>

      <section className="form-section">
        <h3>Strategy Configuration</h3>
        <label>
          Strategy Version
          <input
            value={state.strategyVersion}
            onChange={(event) => update("strategyVersion", event.target.value)}
            required
          />
        </label>
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
        {state.strategyType !== "PAPER_TRADING_SMOKE_TEST" && (
          <>
            <label>
              Position Sizing
              <select
                value={state.positionSizingType}
                onChange={(event) => {
                  const nextType = event.target.value as PositionSizingType;
                  setState((current) => ({
                    ...current,
                    positionSizingType: nextType,
                    positionSizingValue:
                      nextType === "ALL_IN" ? "" : current.positionSizingValue,
                  }));
                }}
              >
                <option value="ALL_IN">ALL_IN</option>
                <option value="FIXED_CASH">FIXED_CASH</option>
                <option value="PERCENT_OF_PORTFOLIO">
                  PERCENT_OF_PORTFOLIO
                </option>
                <option value="FIXED_QUANTITY">FIXED_QUANTITY</option>
              </select>
            </label>
            {state.positionSizingType !== "ALL_IN" && (
              <label>
                Position Sizing Value
                <input
                  min={
                    state.positionSizingType === "PERCENT_OF_PORTFOLIO"
                      ? "0"
                      : "1"
                  }
                  max={
                    state.positionSizingType === "PERCENT_OF_PORTFOLIO"
                      ? "1"
                      : undefined
                  }
                  step={
                    state.positionSizingType === "FIXED_QUANTITY"
                      ? "1"
                      : state.positionSizingType === "PERCENT_OF_PORTFOLIO"
                        ? "0.01"
                        : "0.01"
                  }
                  type="number"
                  value={state.positionSizingValue}
                  onChange={(event) =>
                    update("positionSizingValue", event.target.value)
                  }
                />
              </label>
            )}
          </>
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
      </section>

      <section className="form-section">
        <h3>Risk and Fees</h3>
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
        <div className="state-box state-box-error full-span">
          {validationError || errorMessage(createMutation.error)}
        </div>
      )}

      <div className="button-row full-span">
        <button disabled={createMutation.isPending} type="submit">
          Create Experiment
        </button>
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
      </div>
    </form>
  );
}
