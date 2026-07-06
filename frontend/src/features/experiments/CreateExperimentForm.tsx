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
  strategyCategory: StrategyCategory;
  strategyType: StrategyType;
  aiDecisionPattern: AiDecisionPattern;
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

type StrategyCategory = "RULE_BASED" | "AI_STRATEGY";

type AiDecisionPattern = "SINGLE_AGENT" | "MULTI_AGENT";

const initialState: FormState = {
  name: "",
  mode: "HISTORICAL_SIMULATION",
  strategyCategory: "RULE_BASED",
  strategyType: "BUY_AND_HOLD",
  aiDecisionPattern: "SINGLE_AGENT",
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

const RECOMMENDED_CONFIDENCE_THRESHOLD = "0.60";
const DEFAULT_ASSET_SYMBOL = "SPY";

const STRATEGY_DESCRIPTIONS: Record<StrategyType, string> = {
  BUY_AND_HOLD: "Buy once, then hold the selected asset.",
  MOVING_AVERAGE: "Use a daily moving average signal.",
  AGENTIC_AI: "Use ScaDS.AI-backed paper trading with agent guardrails.",
  OPENING_RANGE_BREAKOUT: "Use 5-minute opening range breakout rules.",
  PAPER_TRADING_SMOKE_TEST: "Run 1-share paper diagnostics only.",
};

const STRATEGY_CATEGORY_DESCRIPTIONS: Record<StrategyCategory, string> = {
  RULE_BASED: "Deterministic strategies with fixed trading rules.",
  AI_STRATEGY: "LLM-backed decision patterns with RiskCheck enforcement.",
};

const AI_PATTERN_OPTIONS: Array<{
  value: AiDecisionPattern;
  label: string;
  description: string;
  enabled: boolean;
}> = [
  {
    value: "SINGLE_AGENT",
    label: "Single Agent",
    description: "One AI agent evaluates market and portfolio context.",
    enabled: true,
  },
  {
    value: "MULTI_AGENT",
    label: "Multi Agent",
    description:
      "A staged workflow combines data, technical, fundamental, sentiment, risk, and portfolio agents.",
    enabled: true,
  },
];

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

function agentModeForPattern(pattern: AiDecisionPattern): AgentMode {
  return pattern === "MULTI_AGENT" ? "PIPELINE" : "SINGLE_AGENT";
}

function frequenciesFor(
  strategyType: StrategyType,
  frequencies: TradingFrequency[],
) {
  if (strategyType === "AGENTIC_AI") {
    return frequencies.filter(
      (frequency) => frequency === "DAILY" || frequency === "HOURLY",
    );
  }
  const defaultFrequency = defaultFrequencyFor(strategyType);
  return frequencies.filter((frequency) => frequency === defaultFrequency);
}

function strategySupportedForMode(
  mode: ExperimentMode,
  strategyType: StrategyType,
) {
  if (mode === "HISTORICAL_SIMULATION") {
    return (
      strategyType !== "AGENTIC_AI"
      && strategyType !== "PAPER_TRADING_SMOKE_TEST"
    );
  }
  return true;
}

function isSpyOnlySelection(mode: ExperimentMode, strategyType: StrategyType) {
  return (
    mode === "HISTORICAL_SIMULATION"
    || strategyType === "OPENING_RANGE_BREAKOUT"
    || strategyType === "PAPER_TRADING_SMOKE_TEST"
  );
}

function assetsForSelection(
  mode: ExperimentMode,
  strategyType: StrategyType,
  assets: string[],
) {
  if (isSpyOnlySelection(mode, strategyType)) {
    return assets.filter((asset) => asset === DEFAULT_ASSET_SYMBOL);
  }
  return assets;
}

function strategiesForMode(mode: ExperimentMode, strategies: StrategyType[]) {
  return strategies.filter((strategy) => strategySupportedForMode(mode, strategy));
}

function ruleBasedStrategies(strategies: StrategyType[]) {
  return strategies.filter((strategy) => strategy !== "AGENTIC_AI");
}

function modeChangeState(
  current: FormState,
  nextMode: ExperimentMode,
  defaultAgentModel: string,
): Partial<FormState> {
  const nextStrategy = strategySupportedForMode(nextMode, current.strategyType)
    ? current.strategyType
    : "BUY_AND_HOLD";

  return {
    mode: nextMode,
    strategyCategory:
      nextMode === "PAPER_TRADING" && nextStrategy === "AGENTIC_AI"
        ? "AI_STRATEGY"
        : "RULE_BASED",
    strategyType: nextStrategy,
    assetSymbol: isSpyOnlySelection(nextMode, nextStrategy)
      ? DEFAULT_ASSET_SYMBOL
      : current.assetSymbol,
    aiDecisionPattern: "SINGLE_AGENT",
    movingAverageWindow:
      nextStrategy === "MOVING_AVERAGE" ? current.movingAverageWindow || "3" : "",
    tradingFrequency: defaultFrequencyFor(nextStrategy),
    agentMode:
      nextMode === "PAPER_TRADING" && nextStrategy === "AGENTIC_AI"
        ? agentModeForPattern("SINGLE_AGENT")
        : "",
    modelName:
      nextMode === "PAPER_TRADING" && nextStrategy === "AGENTIC_AI"
        ? defaultAgentModel
        : "",
    confidenceThreshold:
      nextMode === "PAPER_TRADING" && nextStrategy === "AGENTIC_AI"
        ? current.confidenceThreshold || RECOMMENDED_CONFIDENCE_THRESHOLD
        : current.confidenceThreshold,
  };
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
  if (state.mode === "HISTORICAL_SIMULATION" && state.strategyType === "AGENTIC_AI") {
    return "Agentic AI is available for paper trading only.";
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
    if (state.strategyCategory !== "AI_STRATEGY") {
      return "Agentic AI must be configured through AI Strategy.";
    }
    const expectedAgentMode = agentModeForPattern(state.aiDecisionPattern);
    if (state.agentMode && state.agentMode !== expectedAgentMode) {
      return "Selected AI pattern does not match the persisted agent mode.";
    }
    if (!state.modelName.trim()) {
      return "Paper trading Agentic AI requires a model selection.";
    }
    if (!["DAILY", "HOURLY"].includes(state.tradingFrequency)) {
      return "Paper trading Agentic AI supports DAILY or HOURLY frequency only.";
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
    state.strategyType === "MOVING_AVERAGE"
    || (isPaper && state.strategyType === "AGENTIC_AI");
  const availableStrategies = strategiesForMode(
    state.mode,
    optionsQuery.data?.strategies ?? [],
  );
  const availableRuleBasedStrategies = ruleBasedStrategies(availableStrategies);
  const canUseAiStrategy =
    isPaper && availableStrategies.includes("AGENTIC_AI");
  const scadsaiModels = optionsQuery.data?.scadsaiAllowedModels ?? [];
  const defaultScadsaiModel = scadsaiModels.includes(
    optionsQuery.data?.scadsaiDefaultModel ?? "",
  )
    ? optionsQuery.data?.scadsaiDefaultModel ?? ""
    : scadsaiModels[0] ?? "";
  const hasScadsaiModels = scadsaiModels.length > 0;
  const availableFrequencies = frequenciesFor(
    state.strategyType,
    optionsQuery.data?.tradingFrequencies ?? [],
  );
  const availableAssets = assetsForSelection(
    state.mode,
    state.strategyType,
    optionsQuery.data?.assets ?? [DEFAULT_ASSET_SYMBOL],
  );
  const assetSelectValue = availableAssets.includes(state.assetSymbol)
    ? state.assetSymbol
    : DEFAULT_ASSET_SYMBOL;

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

  const selectRuleBasedCategory = () => {
    setState((current) => {
      const availableRuleStrategies = ruleBasedStrategies(
        strategiesForMode(current.mode, optionsQuery.data.strategies),
      );
      const nextStrategy = availableRuleStrategies.some(
        (strategy) => strategy === current.strategyType,
      )
        ? current.strategyType
        : "BUY_AND_HOLD";
      return {
        ...current,
        strategyCategory: "RULE_BASED",
        strategyType: nextStrategy,
        aiDecisionPattern: "SINGLE_AGENT",
        agentMode: "",
        modelName: "",
        confidenceThreshold: "",
        movingAverageWindow:
          nextStrategy === "MOVING_AVERAGE" ? current.movingAverageWindow || "3" : "",
        tradingFrequency: defaultFrequencyFor(nextStrategy),
        assetSymbol: isSpyOnlySelection(current.mode, nextStrategy)
          ? DEFAULT_ASSET_SYMBOL
          : current.assetSymbol,
      };
    });
  };

  const selectAiCategory = () => {
    setState((current) => ({
      ...current,
      strategyCategory: "AI_STRATEGY",
      strategyType: "AGENTIC_AI",
      aiDecisionPattern: "SINGLE_AGENT",
      movingAverageWindow: "",
      tradingFrequency: "DAILY",
      assetSymbol: current.assetSymbol,
      agentMode: agentModeForPattern("SINGLE_AGENT"),
      modelName: current.modelName || defaultScadsaiModel,
      confidenceThreshold:
        current.confidenceThreshold || RECOMMENDED_CONFIDENCE_THRESHOLD,
    }));
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
      assetSymbol: assetSelectValue,
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
          <strong>
            {state.strategyCategory === "AI_STRATEGY"
              ? formatEnumLabel(state.aiDecisionPattern)
              : formatEnumLabel(state.strategyType)}
          </strong>
        </div>
        <div>
          <span className="summary-label">Asset</span>
          <strong>{assetSelectValue}</strong>
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
                ...modeChangeState(
                  current,
                  nextMode,
                  optionsQuery.data.scadsaiDefaultModel,
                ),
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
        <div className="form-field">
          <span className="field-label">Strategy Category</span>
          {isPaper ? (
            <div className="strategy-category-grid">
              <button
                className={
                  state.strategyCategory === "RULE_BASED"
                    ? "choice-card choice-card-active"
                    : "choice-card"
                }
                type="button"
                onClick={selectRuleBasedCategory}
              >
                <strong>Rule-Based</strong>
                <small>{STRATEGY_CATEGORY_DESCRIPTIONS.RULE_BASED}</small>
              </button>
              <button
                className={
                  state.strategyCategory === "AI_STRATEGY"
                    ? "choice-card choice-card-active"
                    : "choice-card"
                }
                disabled={!canUseAiStrategy}
                type="button"
                onClick={selectAiCategory}
              >
                <strong>AI Strategy</strong>
                <small>{STRATEGY_CATEGORY_DESCRIPTIONS.AI_STRATEGY}</small>
              </button>
            </div>
          ) : (
            <div className="context-note">
              Historical simulations currently support rule-based strategies only.
            </div>
          )}
        </div>
        {state.strategyCategory === "RULE_BASED" && (
          <label>
            Rule-Based Strategy
            <select
              value={state.strategyType}
              onChange={(event) => {
                const nextStrategy = event.target.value as StrategyType;
                setState((current) => ({
                  ...current,
                  strategyCategory: "RULE_BASED",
                  strategyType: nextStrategy,
                  aiDecisionPattern: "SINGLE_AGENT",
                  movingAverageWindow:
                    nextStrategy === "MOVING_AVERAGE" ? "3" : "",
                  tradingFrequency: defaultFrequencyFor(nextStrategy),
                  assetSymbol: isSpyOnlySelection(current.mode, nextStrategy)
                    ? DEFAULT_ASSET_SYMBOL
                    : current.assetSymbol,
                  mode:
                    nextStrategy === "PAPER_TRADING_SMOKE_TEST"
                      ? "PAPER_TRADING"
                      : current.mode,
                  agentMode: "",
                  modelName: "",
                }));
              }}
            >
              {availableRuleBasedStrategies.map((strategy) => (
                <option key={strategy} value={strategy}>
                  {strategy}
                </option>
              ))}
            </select>
            <small>{STRATEGY_DESCRIPTIONS[state.strategyType]}</small>
          </label>
        )}
        {isPaper && state.strategyCategory === "AI_STRATEGY" && (
          <div className="ai-pattern-section">
            <div>
              <span className="field-label">AI Decision Pattern</span>
              <div className="ai-pattern-grid">
                {AI_PATTERN_OPTIONS.map((pattern) => {
                  const isActive = state.aiDecisionPattern === pattern.value;
                  return (
                    <button
                      key={pattern.value}
                      className={
                        isActive
                          ? "choice-card choice-card-active"
                          : "choice-card"
                      }
                      disabled={!pattern.enabled}
                      type="button"
                      onClick={() => {
                        if (!pattern.enabled) return;
                        setState((current) => ({
                          ...current,
                          strategyCategory: "AI_STRATEGY",
                          strategyType: "AGENTIC_AI",
                          aiDecisionPattern: pattern.value,
                          movingAverageWindow: "",
                          tradingFrequency:
                            current.tradingFrequency === "HOURLY"
                            || current.tradingFrequency === "DAILY"
                              ? current.tradingFrequency
                              : "DAILY",
                          agentMode: agentModeForPattern(pattern.value),
                          modelName:
                            current.modelName
                            || defaultScadsaiModel,
                          confidenceThreshold:
                            current.confidenceThreshold
                            || RECOMMENDED_CONFIDENCE_THRESHOLD,
                        }));
                      }}
                    >
                      <span>
                        <strong>{pattern.label}</strong>
                        {!pattern.enabled && (
                          <em className="choice-card-badge">Planned</em>
                        )}
                      </span>
                      <small>{pattern.description}</small>
                    </button>
                  );
                })}
              </div>
            </div>
            <div className="context-note">
              AI output is advisory only. RiskCheck still decides whether a broker
              order may be submitted.
            </div>
          </div>
        )}
        {state.strategyType === "PAPER_TRADING_SMOKE_TEST" && (
          <div className="state-box">
            Smoke-test strategy creates alternating 1-share Alpaca paper BUY/SELL
            orders for operational testing only. It is not an investment strategy.
          </div>
        )}
        <label>
          Asset
          <select
            disabled={availableAssets.length === 1}
            value={assetSelectValue}
            onChange={(event) => update("assetSymbol", event.target.value)}
          >
            {availableAssets.map((asset) => (
              <option key={asset} value={asset}>
                {asset}
              </option>
            ))}
          </select>
          {availableAssets.length === 1 ? (
            <small>
              This mode/strategy currently supports {DEFAULT_ASSET_SYMBOL} only.
            </small>
          ) : (
            <small>
              Paper Buy-and-Hold, Moving Average, and AI strategies support the
              configured US large-cap allowlist.
            </small>
          )}
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
          {isPaper && state.strategyType === "AGENTIC_AI" && (
            <small>
              {state.tradingFrequency === "HOURLY"
                ? "Hourly AI evaluates the latest completed regular-session hourly bar."
                : "Daily AI evaluates the latest completed daily bar close."}
            </small>
          )}
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
        {isPaper && state.strategyType === "AGENTIC_AI" && (
          <>
            <label>
              ScaDS.AI Model
              <select
                disabled={!hasScadsaiModels}
                value={state.modelName || defaultScadsaiModel}
                onChange={(event) => update("modelName", event.target.value)}
              >
                {scadsaiModels.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
              <small>
                {hasScadsaiModels
                  ? "All allowed ScaDS.AI models are loaded from backend configuration."
                  : "No ScaDS.AI models are configured."}
              </small>
            </label>
            <div className="form-field threshold-field">
              <div className="threshold-heading">
                <span className="field-label">Confidence Threshold</span>
                <strong>{state.confidenceThreshold || "None"}</strong>
              </div>
              <div className="threshold-control">
                <input
                  min="0"
                  max="1"
                  step="0.01"
                  type="range"
                  value={
                    state.confidenceThreshold || RECOMMENDED_CONFIDENCE_THRESHOLD
                  }
                  onChange={(event) =>
                    update("confidenceThreshold", event.target.value)
                  }
                />
                <input
                  aria-label="Confidence threshold value"
                  min="0"
                  max="1"
                  step="0.01"
                  type="number"
                  value={state.confidenceThreshold}
                  onChange={(event) =>
                    update("confidenceThreshold", event.target.value)
                  }
                />
              </div>
              <div className="threshold-actions">
                <button
                  type="button"
                  onClick={() =>
                    update(
                      "confidenceThreshold",
                      RECOMMENDED_CONFIDENCE_THRESHOLD,
                    )
                  }
                >
                  Use recommended 0.60
                </button>
              </div>
              <small>
                Minimum confidence before an AI BUY or SELL proposal can proceed.
                Below this value, the system converts the proposal to HOLD before
                RiskCheck. Higher values are more conservative.
              </small>
            </div>
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
