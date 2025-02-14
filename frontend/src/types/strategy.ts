export interface StrategyParam {
    name: string;
    type: 'number' | 'string' | 'boolean';
    default: number | string | boolean;
    min?: number;
    max?: number;
    description: string;
}

export interface Strategy {
    id: string;
    name: string;
    description: string;
    params: StrategyParam[];
}

export interface BacktestConfig {
    strategyId: string;
    params: Record<string, any>;
    symbol: string;
    interval: string;
    startTime?: string;
    endTime?: string;
    initialCapital: number;
}

export interface BacktestResult {
    equity: Array<{
        timestamp: string;
        equity: number;
        position: number;
        returns_pct: number;
    }>;
    trades: Array<{
        timestamp: string;
        action: string;
        price: number;
        size: number;
        pnl: number;
    }>;
    price_data: Array<{
        timestamp: string;
        open: number;
        high: number;
        low: number;
        close: number;
        volume: number;
    }>;
    stats: {
        'Total Return (%)': number;
        'Annual Return (%)': number;
        'Max Drawdown (%)': number;
        'Sharpe Ratio': number;
        'Win Rate (%)': number;
    };
} 