import type en from "./en";

const ko: typeof en = {
  // global
  "site.title": "EPL Prediction Lab",
  "site.tagline": "xG는 거짓말하지 않는다. 북메이커는 다르지만.",
  "nav.fixtures": "경기 일정",
  "nav.table": "순위표",
  "nav.stats": "통계",
  "nav.recent": "지난 주말",
  "nav.scorers": "득점왕",
  "nav.news": "뉴스",
  "common.back": "← 뒤로",
  "common.viewTx": "거래 보기 →",
  "common.season": "시즌",
  "common.noData": "데이터 없음.",
  "common.loading": "로딩 중…",

  // dashboard
  "dash.headline": "이번 주 경기",
  "dash.subhead": "최근 xG 기반 Poisson + Dixon-Coles · Qwen AI 분석.",
  "dash.apiError": "API 오류",
  "dash.empty": "예정된 경기가 없습니다. ingest 및 predict 스크립트를 실행하세요.",
  "dash.stat.accuracy": "모델 정확도",
  "dash.stat.baseline": "기준 (항상 홈)",
  "dash.stat.logloss": "Log-loss",
  "dash.stat.matches": "채점된 경기",

  // match card / status
  "status.scheduled": "예정",
  "status.final": "종료",
  "status.live": "진행 중",
  "match.topScore": "예측 스코어",
  "match.liveScore": "실시간 스코어",
  "match.finalScore": "최종 스코어",
  "match.predictedLabel": "예측",
  "match.actualLabel": "실제",
  "match.pending": "예측 대기 중",
  "match.value": "가치",
  "match.vs": "vs",

  // match detail
  "detail.breadcrumb": "경기 #{id} • {date} • {status}",
  "detail.expectedGoals": "기대 득점 (λ)",
  "detail.home": "홈",
  "detail.draw": "무",
  "detail.away": "원정",
  "detail.pendingPost": "예측 대기 — POST /api/predictions/{id}",
  "detail.analysis": "분석",
  "detail.scoreMatrix.title": "스코어 확률",
  "detail.scoreMatrix.top": "가장 가능성 높음",
  "detail.scoreMatrix.footer": "각 셀은 해당 스코어 확률. λ_home={lamH}, λ_away={lamA}, ρ={rho} 에서 도출.",

  // fingerprint
  "fp.title": "예측 지문",
  "fp.badge": "검증 가능",
  "fp.explain": "예측 본문의 결정적 SHA-256. 공개 데이터로 재계산해 모델 관점이 변조되지 않았음을 확인.",

  // odds
  "odds.title": "베팅 배당",
  "odds.outcome": "결과",
  "odds.odds": "배당",
  "odds.fair": "공정 %",
  "odds.edge": "모델 차이",
  "odds.valueHint": "모델은 {outcome}에서 {edge}의 가치를 봅니다. 모델과 시장이 다를 수 있습니다 — 스스로 판단하세요.",

  // table
  "table.title": "xG 순위표",
  "table.subhead": "실제 포인트는 일어난 일. xG 차이는 일어났어야 할 일.",
  "table.empty": "{season} 시즌에 종료된 경기가 없습니다.",
  "table.col.rank": "#",
  "table.col.team": "팀",
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
  "stats.title": "모델 캘리브레이션",
  "stats.subhead": "모델은 자신의 확신을 알까요? 아래 신뢰도 분해가 어떤 숫자를 믿을지 알려줍니다.",
  "stats.brier": "Brier 점수",
  "stats.bins.title": "신뢰 구간별 신뢰도",
  "stats.bins.hint": "모델이 정직하다면 실제 적중률은 각 구간에 들어야 합니다. Δ 양 = 겸손 · 음 = 과신.",
  "stats.bins.empty": "계산할 경기가 부족합니다.",
  "stats.bins.bin": "구간",
  "stats.bins.n": "경기",
  "stats.bins.pred": "예측",
  "stats.bins.actual": "실제",
  "stats.bins.delta": "Δpp",
  "stats.bins.reliability": "신뢰도",
  "stats.weekly.title": "주간 정확도",
  "stats.weekly.hint": "기준선 = 항상 홈 = {baseline}. 더 높은 막대는 단순 선택을 이긴 것.",

  // team profile
  "team.played": "경기 수",
  "team.record": "W-D-L",
  "team.points": "승점",
  "team.goals": "득점 (GF–GA)",
  "team.xgDiff": "xG 차이",
  "team.form": "폼 (최근 10경기)",
  "team.form.none": "종료 경기 없음.",
  "team.topScorers": "득점왕",
  "team.topScorers.empty": "선수 통계가 아직 수집되지 않았습니다. scripts/ingest_players.py --season {season}.",
  "team.recent": "최근 경기",
  "team.upcoming": "예정 경기",
  "team.none": "(없음)",
  "team.trajectoryTitle": "폼 궤적 (5경기 롤링 xG)",
  "team.trajectoryMatches": "경기",
  "team.trajectoryXgFor": "xG 득점 {value}",
  "team.trajectoryXgAgainst": "xG 실점 {value}",
  "team.trajectoryFooter": "녹색선 = 넣어야 할 골. 빨간선 = 실점해야 할 골. 교차 = 시즌 전환점.",

  // chat widget
  "chat.title": "분석가에게 질문",
  "chat.placeholder": "이 경기에 대해 무엇이든 물어보세요…",
  "chat.send": "전송",
  "chat.streaming": "생각 중…",
  "chat.empty": "이 경기에 대해 질문하세요 — 또는 아래 제안을 누르세요.",
  "chat.error": "오류가 발생했습니다.",
  "chat.you": "당신",
  "chat.bot": "분석가",

  // recent
  "recent.title": "지난주 모델 성적",
  "recent.subhead": "최근 {days}일 종료 경기, 킥오프 전 모델 선택과 적중 여부.",
  "recent.empty": "최근 {days}일 종료 경기 없음.",
  "recent.summary.scored": "경기 수",
  "recent.summary.accuracy": "정확도",
  "recent.summary.logloss": "Log-loss",
  "recent.summary.correct": "적중",
  "recent.hit": "적중",
  "recent.miss": "실패",
  "recent.predicted": "모델 선택",
  "recent.actual": "결과",

  // ROI
  "roi.title": "가치 베팅 손익",
  "roi.subhead": "이번 시즌 모델 차이 ≥ {threshold}pp 인 모든 베팅에 1u 고정 베팅 시 누적 수익.",
  "roi.totalBets": "베팅",
  "roi.totalPnl": "P&L (단위)",
  "roi.roi": "ROI",
  "roi.empty": "임계값을 넘은 베팅 없음.",

  // quick picks
  "quick.title": "이번 주 최고 가치",
  "quick.empty": "이번 주 강한 가치 베팅 없음.",
  "quick.edge": "차이",

  // scorers
  "scorers.title": "{season} 득점왕",
  "scorers.subhead": "누가 득점왕 경쟁을 이끌고 있는지 — xG 모델은 누가 운이 좋았는지 알려줍니다.",
  "scorers.sortGoals": "득점",
  "scorers.sortXg": "xG",
  "scorers.sortAssists": "어시스트",
  "scorers.sortDelta": "G − xG",
  "scorers.empty": "{season} 시즌 선수 데이터 없음.",
  "events.title": "무슨 일이 있었나",
  "events.goals": "득점",
  "events.cards": "카드",
  "events.subs": "교체",

  // H2H
  "h2h.title": "최근 {n} 경기",
  "h2h.empty": "DB에 이전 맞대결 없음.",
  "h2h.homeWins": "{team} 승",
  "h2h.awayWins": "{team} 승",
  "h2h.draws": "무",
};

export default ko;
