import { GoogleGenAI, Type } from "@google/genai";
import { Stock } from "../types";

// Initialize Gemini Client
const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

const MODEL_NAME = 'gemini-3-flash-preview';

export const analyzeStockDeeply = async (stock: Stock): Promise<string> => {
  try {
    const prompt = `
      请对以下股票进行深度金融分析：${stock.name} (代码: ${stock.code})。
      
      请扮演一位资深A股/港股分析师，利用Google Search获取今日最新的实时行情、新闻和公告，并生成一份专业的分析报告。
      
      报告应包含以下章节（请使用Markdown格式）：

      1. **实时行情与市场背景 (Real-time Context)**
         - 今日股价表现及近期走势。
         - 影响今日走势的重大新闻或行业消息。

      2. **技术面分析 (Technical Analysis)**
         - 关键支撑位与压力位。
         - 主要技术指标形态（如MACD, KDJ, 均线系统等）的解读。

      3. **基本面亮点 (Fundamental Highlights)**
         - 估值水平（PE/PB）与行业对比。
         - 近期财报或业绩预告的核心观点。
         - 机构资金流向（如有）。

      4. **风险评估 (Risk Assessment)**
         - 当前面临的主要风险（政策、市场、经营等）。
         - 波动性评估（高/中/低）。

      5. **操作建议 (Actionable Advice)**
         - 明确给出：**买入 (Buy)** / **增持 (Add)** / **持有 (Hold)** / **减仓 (Reduce)** / **卖出 (Sell)** 的建议。
         - 附带详细的逻辑理由。

      请确保所有信息基于最新数据，语言风格专业且通俗易懂。
    `;

    const response = await ai.models.generateContent({
      model: MODEL_NAME,
      contents: prompt,
      config: {
        tools: [{ googleSearch: {} }],
        systemInstruction: "你是一位拥有20年经验的资深金融分析师，专门服务于中国A股和港股市场的个人投资者。",
      },
    });

    let text = response.text || "无法生成分析报告，请稍后再试。";
    
    // Append sources
    const sources = response.candidates?.[0]?.groundingMetadata?.groundingChunks
      ?.map((chunk: any) => chunk.web?.uri)
      .filter((uri: string) => !!uri);

    if (sources && sources.length > 0) {
      text += `\n\n**参考来源:**\n${sources.map((s: string) => `- [${new URL(s).hostname}](${s})`).join('\n')}`;
    }

    return text;

  } catch (error) {
    console.error("Analysis Error:", error);
    throw new Error("分析失败，请检查网络或稍后再试。");
  }
};

export const generateDailyStrategy = async (portfolio: Stock[]): Promise<string> => {
  try {
    const portfolioList = portfolio.map(s => `- ${s.name} (${s.code})`).join('\n');
    
    const prompt = `
      我持有以下股票投资组合（关注列表）：
      ${portfolioList}

      请作为我的“私人投资顾问”，结合**今日**的宏观经济数据、市场情绪指数、行业热点以及我关注的股票，生成一份深度的**【每日投资策略报告】**。

      报告结构必须包含以下部分（使用Markdown格式）：

      ### 1. 市场整体走势判断 (Market Overview)
      - 利用Google Search分析今日A股/港股大盘走势（上证指数、恒生指数等）。
      - 宏观经济数据解读（如PMI、利率决议、央行操作等）。
      - 市场情绪评估（贪婪/恐慌、成交量变化）。

      ### 2. 行业热点与板块轮动 (Sector Trends)
      - 今日市场的主线热点是什么？（例如：机器人、贵金属、医药、科技等）。
      - 我的持仓中有哪些股票属于今日的热点板块？
      - 哪些板块正在退潮，需要警惕？

      ### 3. 持仓个股深度扫描 (Portfolio Scan)
      - 针对我关注列表中的股票，挑选出今日**异动明显**或**消息面重大**的2-3只进行重点点评。
      - 简要说明其他持仓的表现。

      ### 4. 今日操作建议 (Daily Strategy)
      - **加仓/买入机会**：是否有标的出现回调买点？
      - **减仓/止盈建议**：是否有标的触及压力位或基本面恶化？
      - **持仓观望**：哪些适合继续持有不动？
      
      ### 5. 风险提示 (Risk Warning)
      - 今日交易需要注意的特定风险点。

      请确保数据实时、观点鲜明、建议具备可操作性。语言使用中文。
    `;

    const response = await ai.models.generateContent({
      model: MODEL_NAME,
      contents: prompt,
      config: {
        tools: [{ googleSearch: {} }],
        systemInstruction: "你是一位专业的投资策略师，擅长根据宏观面和技术面制定每日交易计划。",
      },
    });

    let text = response.text || "无法生成策略报告。";
     const sources = response.candidates?.[0]?.groundingMetadata?.groundingChunks
      ?.map((chunk: any) => chunk.web?.uri)
      .filter((uri: string) => !!uri);

    if (sources && sources.length > 0) {
      text += `\n\n**相关新闻资讯:**\n${sources.map((s: string) => `- [来源](${s})`).join('\n')}`;
    }

    return text;

  } catch (error) {
    console.error("Strategy Error:", error);
    throw new Error("策略生成失败，请重试。");
  }
};

export const identifyStockInfo = async (code: string): Promise<Stock> => {
  try {
    const prompt = `识别股票代码 "${code}" 对应的中文名称和类型（股票、ETF、基金）。
    返回JSON格式: { "name": "股票名称", "type": "Stock" | "ETF" | "Fund" }`;
    
    const response = await ai.models.generateContent({
      model: MODEL_NAME,
      contents: prompt,
      config: {
        responseMimeType: "application/json",
         responseSchema: {
            type: Type.OBJECT,
            properties: {
              name: { type: Type.STRING },
              type: { type: Type.STRING }
            },
            required: ["name", "type"]
         }
      }
    });

    const data = JSON.parse(response.text || "{}");
    return {
      code,
      name: data.name || "未知股票",
      type: data.type || "Stock"
    };
  } catch (e) {
    return { code, name: "未知", type: "Stock" };
  }
}