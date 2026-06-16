export interface Stock {
  code: string;
  name: string;
  type: 'Stock' | 'ETF' | 'Fund' | 'Unknown';
}

export interface AnalysisResult {
  stockCode: string;
  content: string;
  timestamp: number;
}

export interface StrategyResult {
  content: string;
  timestamp: number;
}

export enum LoadingState {
  IDLE = 'IDLE',
  LOADING = 'LOADING',
  SUCCESS = 'SUCCESS',
  ERROR = 'ERROR'
}