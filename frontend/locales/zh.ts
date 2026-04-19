import type en from "./en";

const zh: typeof en = {
  // global
  "site.title": "EPL Prediction Lab",
  "site.tagline": "xG 不会说谎,庄家会。",
  "nav.fixtures": "赛程",
  "nav.table": "积分榜",
  "nav.stats": "统计",
  "nav.recent": "上周末",
  "nav.scorers": "射手榜",
  "common.back": "← 返回",
  "common.viewTx": "查看交易 →",
  "common.season": "赛季",
  "common.noData": "暂无数据。",
  "common.loading": "加载中…",

  // dashboard
  "dash.headline": "本周比赛",
  "dash.subhead": "基于近期 xG 的 Poisson + Dixon-Coles 模型 · Qwen AI 分析。",
  "dash.apiError": "API 错误",
  "dash.empty": "暂无即将到来的比赛。请运行 ingest 和 predict 脚本。",
  "dash.stat.accuracy": "模型准确率",
  "dash.stat.baseline": "基线(主场必选)",
  "dash.stat.logloss": "对数损失",
  "dash.stat.matches": "已评分场次",

  // match card / status
  "status.scheduled": "即将开始",
  "status.final": "已结束",
  "status.live": "直播中",
  "match.topScore": "预测比分",
  "match.liveScore": "实时比分",
  "match.finalScore": "最终比分",
  "match.predictedLabel": "预测",
  "match.actualLabel": "实际",
  "match.pending": "预测待定",
  "match.value": "价值",
  "match.vs": "vs",

  // match detail
  "detail.breadcrumb": "比赛 #{id} • {date} • {status}",
  "detail.expectedGoals": "预期进球 (λ)",
  "detail.home": "主队",
  "detail.draw": "平局",
  "detail.away": "客队",
  "detail.pendingPost": "预测待定 — POST /api/predictions/{id}",
  "detail.analysis": "分析",
  "detail.scoreMatrix.title": "比分概率",
  "detail.scoreMatrix.top": "最可能",
  "detail.scoreMatrix.footer": "每一格是该比分发生的概率。由 λ_home={lamH}, λ_away={lamA}, ρ={rho} 推导。",

  // fingerprint
  "fp.title": "预测指纹",
  "fp.badge": "可验证",
  "fp.explain": "预测正文的确定性 SHA-256 哈希。从公开数据重新计算以验证模型观点未被篡改。",

  // odds
  "odds.title": "博彩赔率",
  "odds.outcome": "结果",
  "odds.odds": "赔率",
  "odds.fair": "公平 %",
  "odds.edge": "模型差值",
  "odds.valueHint": "模型在 {outcome} 上看到 {edge} 的价值。模型和市场可能不一致 — 请自行判断。",

  // table
  "table.title": "xG 积分榜",
  "table.subhead": "实际积分是发生了什么。xG 差值是应该发生什么。",
  "table.empty": "{season} 赛季尚无已完成的比赛。",
  "table.col.rank": "#",
  "table.col.team": "球队",
  "table.col.played": "P",
  "table.col.wins": "W",
  "table.col.draws": "D",
  "table.col.losses": "L",
  "table.col.gf": "GF",
  "table.col.ga": "GA",
  "table.col.gd": "GD",
  "table.col.xgf": "xGF",
  "table.col.xga": "xGA",
  "table.col.xgd": "xGD",

  // stats
  "stats.title": "模型校准",
  "stats.subhead": "模型知道自己有多确定吗?下方置信度分解告诉你哪些数字可信。",
  "stats.brier": "Brier 分数",
  "stats.bins.title": "置信度可靠性",
  "stats.bins.hint": "如果模型诚实,实际命中率应落在每个区间。Δ 为正 = 保守;Δ 为负 = 过度自信。",
  "stats.bins.empty": "评分场次不足,无法计算。",
  "stats.bins.bin": "区间",
  "stats.bins.n": "场次",
  "stats.bins.pred": "预测",
  "stats.bins.actual": "实际",
  "stats.bins.delta": "Δpp",
  "stats.bins.reliability": "可靠性",
  "stats.weekly.title": "每周准确率",
  "stats.weekly.hint": "基线线 = 永选主场 = {baseline}。柱高于此表示胜过朴素选择。",

  // team profile
  "team.played": "已赛",
  "team.record": "W-D-L",
  "team.points": "积分",
  "team.goals": "进球 (GF–GA)",
  "team.xgDiff": "xG 差",
  "team.form": "状态(最近 10 场)",
  "team.form.none": "尚无已完成比赛。",
  "team.topScorers": "射手榜",
  "team.topScorers.empty": "尚未摄取球员数据。运行 scripts/ingest_players.py --season {season}。",
  "team.recent": "近期比赛",
  "team.upcoming": "即将比赛",
  "team.none": "(无)",
  "team.trajectoryTitle": "状态轨迹(5 场滚动 xG)",
  "team.trajectoryMatches": "场",
  "team.trajectoryXgFor": "xG 进 {value}",
  "team.trajectoryXgAgainst": "xG 失 {value}",
  "team.trajectoryFooter": "绿线 = 球队应该进的球。红线 = 应该失的球。交叉 = 赛季转折。",

  // chat widget
  "chat.title": "询问分析师",
  "chat.placeholder": "关于这场比赛问任何问题…",
  "chat.send": "发送",
  "chat.streaming": "思考中…",
  "chat.empty": "提出关于这场比赛的问题 — 或点击下方建议。",
  "chat.error": "出错了。",
  "chat.you": "你",
  "chat.bot": "分析师",

  // recent
  "recent.title": "上周模型表现",
  "recent.subhead": "最近 {days} 天的已完成比赛,含模型开球前选择与是否命中。",
  "recent.empty": "最近 {days} 天无已完成比赛。",
  "recent.summary.scored": "场次",
  "recent.summary.accuracy": "准确率",
  "recent.summary.logloss": "对数损失",
  "recent.summary.correct": "猜中",
  "recent.hit": "命中",
  "recent.miss": "未中",
  "recent.predicted": "模型选",
  "recent.actual": "结果",

  // ROI
  "roi.title": "价值投注盈亏",
  "roi.subhead": "如果本赛季对每个模型差值 ≥ {threshold}pp 的投注平均下注 1u 的累计利润。",
  "roi.totalBets": "投注数",
  "roi.totalPnl": "P&L(单位)",
  "roi.roi": "ROI",
  "roi.empty": "暂无投注达到阈值。",

  // quick picks
  "quick.title": "本周最佳价值",
  "quick.empty": "本周暂无强价值投注。",
  "quick.edge": "差值",

  // scorers
  "scorers.title": "{season} 射手榜",
  "scorers.subhead": "谁在{season}金靴奖竞争中领先 — 以及 xG 模型说谁靠运气。",
  "scorers.sortGoals": "进球",
  "scorers.sortXg": "xG",
  "scorers.sortAssists": "助攻",
  "scorers.sortDelta": "进球 − xG",
  "scorers.empty": "尚未摄取 {season} 赛季球员数据。",
  "events.title": "发生了什么",
  "events.goals": "进球",
  "events.cards": "黄红牌",
  "events.subs": "换人",

  // H2H
  "h2h.title": "最近 {n} 次交锋",
  "h2h.empty": "数据库中暂无历史交锋。",
  "h2h.homeWins": "{team} 胜",
  "h2h.awayWins": "{team} 胜",
  "h2h.draws": "平局",
};

export default zh;
