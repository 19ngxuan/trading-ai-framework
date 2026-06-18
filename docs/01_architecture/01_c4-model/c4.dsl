workspace "Trading Lab" "C4 architecture model for a FastAPI modular monolith trading/backtesting system." {

    model {
        user = person "User" "Configures experiments, monitors runs, and reviews metrics."

        marketDataProvider = softwareSystem "Market Data Provider" "Provides OHLCV market data and technical indicators."
        brokerApi = softwareSystem "Broker API" "Executes paper-trading orders and provides broker state."
        llmProvider = softwareSystem "LLM Provider" "Provides language-model reasoning for agentic trading decisions."

        tradingLab = softwareSystem "Trading Lab" "Runs historical simulations and paper-trading experiments." {

            frontend = container "Web Frontend" "Dashboard for experiment configuration, execution monitoring, metrics, and agent logs." "React / TypeScript" {
                tags "Frontend"
            }

            backend = container "Backend API" "Modular monolith exposing HTTP APIs and orchestrating experiment execution." "FastAPI / Python" {
                tags "Backend"

                apiRoutes = component "API Routes" "Defines HTTP endpoints for experiments, executions, metrics, and agent logs." "FastAPI Routers"

                experimentModule = component "Experiment Module" "Manages experiment lifecycle, status transitions, and high-level orchestration." "Python Module"

                strategyModule = component "Strategy Module" "Evaluates rule-based strategies such as Buy and Hold and Moving Average." "Python Module"

                agentModule = component "Agent Module" "Runs agentic AI decision pipelines and records agent decision logs." "Python Module"

                riskModule = component "Risk Module" "Validates trading decisions before orders are created." "Python Module"

                executionModule = component "Execution Module" "Creates and executes execution steps for historical, scheduled, and manual runs." "Python Module"

                marketDataModule = component "Market Data Module" "Loads market data snapshots used by strategy and agent decisions." "Python Module"

                brokerModule = component "Broker Module" "Submits orders to broker APIs and synchronizes broker state." "Python Module"

                metricsModule = component "Metrics Module" "Computes portfolio performance, returns, drawdown, and benchmark comparison." "Python Module"

                schedulerModule = component "Scheduler Module" "Triggers scheduled historical and paper-trading execution steps." "Python Module"

                persistenceLayer = component "Persistence Layer" "Provides database access through repositories, models, and migrations." "SQLAlchemy / Alembic"

                domainModel = component "Domain Model" "Contains domain models, enums, and value objects." "Python Domain Model"
            }

            database = container "Database" "Stores experiments, strategy configs, execution steps, snapshots, decisions, orders, trades, metrics, and logs." "PostgreSQL" {
                tags "Database"
            }
        }

        user -> frontend "Uses"
        frontend -> backend "Calls REST API" "HTTPS / JSON"

        backend -> database "Reads and writes experiment state" "SQL"
        backend -> marketDataProvider "Fetches market data" "HTTP API"
        backend -> brokerApi "Submits orders and syncs broker state" "HTTP API"
        backend -> llmProvider "Requests agent decisions" "HTTP API"

        apiRoutes -> experimentModule "Delegates experiment commands and queries"
        apiRoutes -> executionModule "Starts or inspects execution steps"
        apiRoutes -> metricsModule "Reads metrics and performance data"
        apiRoutes -> agentModule "Reads agent logs"

        experimentModule -> strategyModule "Uses configured strategy"
        experimentModule -> executionModule "Creates execution steps"
        experimentModule -> persistenceLayer "Persists experiment state"

        executionModule -> marketDataModule "Loads market data snapshot"
        executionModule -> strategyModule "Requests rule-based decision"
        executionModule -> agentModule "Requests agentic decision"
        executionModule -> riskModule "Validates decision"
        executionModule -> brokerModule "Creates/submits order"
        executionModule -> metricsModule "Updates portfolio and metrics"
        executionModule -> persistenceLayer "Stores execution step data"

        strategyModule -> domainModel "Uses strategy enums and value objects"
        agentModule -> llmProvider "Calls LLM"
        agentModule -> persistenceLayer "Stores agent decision logs"

        riskModule -> domainModel "Uses risk rules and value objects"
        brokerModule -> brokerApi "Calls broker"
        brokerModule -> persistenceLayer "Stores orders, trades, and broker sync logs"

        marketDataModule -> marketDataProvider "Fetches OHLCV data"
        marketDataModule -> persistenceLayer "Stores market data snapshots"

        metricsModule -> persistenceLayer "Reads trades and portfolio snapshots"
        persistenceLayer -> database "Reads and writes" "SQL"
    }

    views {
        systemContext tradingLab "SystemContext" {
            include *
            autolayout lr
        }

        container tradingLab "Containers" {
            include *
            autolayout lr
        }

        component backend "BackendComponents" {
            include *
            autolayout lr
        }

        styles {
            element "Person" {
                shape person
                background #08427b
                color #ffffff
            }

            element "Software System" {
                background #1168bd
                color #ffffff
            }

            element "Container" {
                background #438dd5
                color #ffffff
            }

            element "Component" {
                background #85bbf0
                color #000000
            }

            element "Frontend" {
                background #7b61ff
                color #ffffff
            }

            element "Backend" {
                background #2f80ed
                color #ffffff
            }

            element "Database" {
                shape cylinder
                background #f5a623
                color #000000
            }
        }
    }
}
