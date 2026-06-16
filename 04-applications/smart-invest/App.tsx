import React, { useState, useEffect } from 'react';
import { Plus, Trash2, TrendingUp, BarChart2, Search, BrainCircuit, Activity } from 'lucide-react';
import { Stock, AnalysisResult, LoadingState } from './types';
import * as GeminiService from './services/geminiService';
import Button from './components/Button';
import Modal from './components/Modal';
import AnalysisDisplay from './components/AnalysisDisplay';

// Initial Data Set updated to user request
const INITIAL_STOCKS: Stock[] = [
  { code: '600497', name: '驰宏锌锗', type: 'Stock' },
  { code: '600513', name: '联环药业', type: 'Stock' },
  { code: '000426', name: '兴业银锡', type: 'Stock' },
  { code: '588000', name: '科创50ETF', type: 'ETF' },
  { code: '600489', name: '中金黄金', type: 'Stock' },
  { code: '513330', name: '恒生互联网ETF', type: 'ETF' },
  { code: '002657', name: '中科金财', type: 'Stock' },
  { code: '002050', name: '三花智控', type: 'Stock' },
  { code: '159530', name: '机器人ETF', type: 'ETF' },
];

const App: React.FC = () => {
  // State Management
  const [stocks, setStocks] = useState<Stock[]>(() => {
    const saved = localStorage.getItem('my_stocks');
    return saved ? JSON.parse(saved) : INITIAL_STOCKS;
  });

  const [analyzingStock, setAnalyzingStock] = useState<string | null>(null); // Code of stock being analyzed
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  
  const [isStrategyLoading, setIsStrategyLoading] = useState(false);
  const [strategyResult, setStrategyResult] = useState<string | null>(null);

  // Modal States
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isAnalysisModalOpen, setIsAnalysisModalOpen] = useState(false);
  const [isStrategyModalOpen, setIsStrategyModalOpen] = useState(false);
  const [stockToDelete, setStockToDelete] = useState<Stock | null>(null);
  
  // Add Form State
  const [newStockCode, setNewStockCode] = useState('');
  const [newStockName, setNewStockName] = useState('');
  const [isIdentifying, setIsIdentifying] = useState(false);

  // Persistence
  useEffect(() => {
    localStorage.setItem('my_stocks', JSON.stringify(stocks));
  }, [stocks]);

  // Handlers
  const handleAnalyze = async (stock: Stock) => {
    setAnalyzingStock(stock.code);
    setIsAnalysisModalOpen(true);
    setAnalysisResult(null); // Reset previous result

    try {
      const markdown = await GeminiService.analyzeStockDeeply(stock);
      setAnalysisResult({
        stockCode: stock.code,
        content: markdown,
        timestamp: Date.now()
      });
    } catch (error) {
      setAnalysisResult({
        stockCode: stock.code,
        content: "分析失败，请稍后重试。",
        timestamp: Date.now()
      });
    } finally {
      setAnalyzingStock(null);
    }
  };

  const handleGenerateStrategy = async () => {
    setIsStrategyLoading(true);
    setIsStrategyModalOpen(true);
    setStrategyResult(null);
    try {
      const result = await GeminiService.generateDailyStrategy(stocks);
      setStrategyResult(result);
    } catch (error) {
      setStrategyResult("无法生成策略报告。");
    } finally {
      setIsStrategyLoading(false);
    }
  };

  const confirmDelete = (stock: Stock) => {
    setStockToDelete(stock);
    setIsDeleteModalOpen(true);
  };

  const handleDelete = () => {
    if (stockToDelete) {
      setStocks(prev => prev.filter(s => s.code !== stockToDelete.code));
      setIsDeleteModalOpen(false);
      setStockToDelete(null);
    }
  };

  const handleIdentifyAndAdd = async () => {
    if (!newStockCode) return;
    setIsIdentifying(true);
    try {
      // If user provided name, use it, otherwise ask AI
      let stockToAdd: Stock;
      if (newStockName) {
        stockToAdd = {
          code: newStockCode,
          name: newStockName,
          type: 'Stock' // Default
        };
      } else {
         stockToAdd = await GeminiService.identifyStockInfo(newStockCode);
      }
      
      // Check duplicate
      if (stocks.some(s => s.code === stockToAdd.code)) {
        alert("该股票已在列表中！");
      } else {
        setStocks(prev => [...prev, stockToAdd]);
        setIsAddModalOpen(false);
        setNewStockCode('');
        setNewStockName('');
      }
    } catch (e) {
      alert("无法识别该股票，请手动输入名称。");
    } finally {
      setIsIdentifying(false);
    }
  };

  return (
    <div className="min-h-screen pb-12">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-30 shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-lg">
              <TrendingUp className="text-white h-6 w-6" />
            </div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-teal-300">
              SmartInvest AI
            </h1>
          </div>
          <div className="flex gap-3">
            <Button 
              variant="secondary" 
              onClick={handleGenerateStrategy}
              disabled={isStrategyLoading}
            >
              <BrainCircuit size={18} />
              <span className="hidden sm:inline">生成每日策略</span>
            </Button>
            <Button onClick={() => setIsAddModalOpen(true)}>
              <Plus size={18} />
              <span className="hidden sm:inline">添加股票</span>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Stats / Overview Strip */}
        <div className="mb-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl flex items-center gap-4">
             <div className="p-3 bg-indigo-500/20 rounded-full text-indigo-400">
                <BarChart2 size={24} />
             </div>
             <div>
                <p className="text-slate-400 text-sm">关注资产总数</p>
                <p className="text-2xl font-bold text-white">{stocks.length}</p>
             </div>
          </div>
          <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl flex items-center gap-4">
             <div className="p-3 bg-teal-500/20 rounded-full text-teal-400">
                <Activity size={24} />
             </div>
             <div>
                <p className="text-slate-400 text-sm">市场状态</p>
                <p className="text-lg font-semibold text-white">实时监控中</p>
             </div>
          </div>
           {/* Hint Card */}
          <div className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 border border-slate-700 p-4 rounded-xl flex items-center justify-between">
             <div className="text-sm text-slate-300">
                想要深度洞察？点击卡片上的 <span className="font-bold text-blue-300">深度分析</span> 获取基于AI的实时研报。
             </div>
          </div>
        </div>

        {/* Stock Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {stocks.map((stock) => (
            <div 
              key={stock.code} 
              className="group bg-slate-800 border border-slate-700 rounded-xl p-5 hover:border-blue-500/50 hover:shadow-xl hover:shadow-blue-900/10 transition-all duration-300 flex flex-col justify-between"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-bold text-slate-100 group-hover:text-blue-300 transition-colors">
                    {stock.name}
                  </h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-sm font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded">
                      {stock.code}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${stock.type === 'ETF' ? 'bg-purple-500/20 text-purple-300' : 'bg-teal-500/20 text-teal-300'}`}>
                      {stock.type}
                    </span>
                  </div>
                </div>
                <button 
                  onClick={() => confirmDelete(stock)}
                  className="text-slate-500 hover:text-red-400 transition-colors p-1"
                  title="删除自选股"
                >
                  <Trash2 size={18} />
                </button>
              </div>

              <div className="mt-4 pt-4 border-t border-slate-700/50 flex gap-3">
                <Button 
                  variant="primary" 
                  className="flex-1 text-sm py-2"
                  onClick={() => handleAnalyze(stock)}
                >
                  <Search size={16} />
                  深度分析
                </Button>
              </div>
            </div>
          ))}
        </div>
        
        {stocks.length === 0 && (
          <div className="text-center py-20 border-2 border-dashed border-slate-700 rounded-2xl bg-slate-800/30">
            <h3 className="text-xl text-slate-400 font-semibold mb-2">您的自选列表为空</h3>
            <p className="text-slate-500 mb-6">请添加股票或ETF开始追踪。</p>
            <Button onClick={() => setIsAddModalOpen(true)}>添加第一只股票</Button>
          </div>
        )}
      </main>

      {/* --- Modals --- */}

      {/* Add Stock Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="添加自选股"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">股票代码</label>
            <input 
              type="text" 
              value={newStockCode}
              onChange={(e) => setNewStockCode(e.target.value)}
              placeholder="例如：600519" 
              className="w-full bg-slate-800 border border-slate-600 rounded-lg p-3 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">名称 (可选)</label>
            <input 
              type="text" 
              value={newStockName}
              onChange={(e) => setNewStockName(e.target.value)}
              placeholder="例如：贵州茅台 (留空则自动识别)" 
              className="w-full bg-slate-800 border border-slate-600 rounded-lg p-3 text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
          </div>
          <div className="pt-2 flex justify-end gap-3">
            <Button variant="ghost" onClick={() => setIsAddModalOpen(false)}>取消</Button>
            <Button 
              onClick={handleIdentifyAndAdd} 
              disabled={!newStockCode} 
              isLoading={isIdentifying}
            >
              确认添加
            </Button>
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="确认删除"
      >
        <div className="text-slate-300 mb-6">
          您确定要从自选列表中删除 <span className="font-bold text-white">{stockToDelete?.name}</span> ({stockToDelete?.code}) 吗？
          <br/>
          此操作无法撤销。
        </div>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)}>取消</Button>
          <Button variant="danger" onClick={handleDelete}>删除</Button>
        </div>
      </Modal>

      {/* Analysis Result Modal */}
      <Modal
        isOpen={isAnalysisModalOpen}
        onClose={() => setIsAnalysisModalOpen(false)}
        title={analyzingStock ? `正在分析 ${stocks.find(s => s.code === analyzingStock)?.name}...` : `分析报告: ${analysisResult?.stockCode}`}
        maxWidth="max-w-3xl"
      >
        {analyzingStock ? (
          <div className="py-12 flex flex-col items-center justify-center text-slate-400 space-y-4">
            <div className="relative w-16 h-16">
               <div className="absolute top-0 left-0 w-full h-full border-4 border-blue-500/30 rounded-full"></div>
               <div className="absolute top-0 left-0 w-full h-full border-4 border-t-blue-500 rounded-full animate-spin"></div>
            </div>
            <p className="animate-pulse">正在查询实时市场数据与新闻...</p>
          </div>
        ) : (
          <div className="bg-slate-800/50 rounded-lg p-2">
            {analysisResult && <AnalysisDisplay content={analysisResult.content} />}
            <div className="mt-6 pt-4 border-t border-slate-700 flex justify-end">
               <Button onClick={() => setIsAnalysisModalOpen(false)}>关闭</Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Strategy Modal */}
      <Modal
        isOpen={isStrategyModalOpen}
        onClose={() => setIsStrategyModalOpen(false)}
        title="每日投资策略报告"
        maxWidth="max-w-4xl"
      >
        {isStrategyLoading ? (
          <div className="py-12 flex flex-col items-center justify-center text-slate-400 space-y-4">
             <BrainCircuit size={48} className="animate-pulse text-purple-500" />
             <p>正在综合宏观数据、市场情绪与持仓信息...</p>
          </div>
        ) : (
          <div>
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700 shadow-inner">
               {strategyResult && <AnalysisDisplay content={strategyResult} />}
            </div>
            <div className="mt-6 flex justify-end">
              <Button onClick={() => setIsStrategyModalOpen(false)}>完成</Button>
            </div>
          </div>
        )}
      </Modal>

    </div>
  );
};

export default App;