import type en from "./en";

const vi: typeof en = {
  // global
  "site.title": "EPL Prediction Lab",
  "site.tagline": "xG không nói dối. Nhà cái thì khác.",
  "nav.fixtures": "Lịch đấu",
  "nav.table": "Bảng XH",
  "nav.stats": "Thống kê",
  "nav.recent": "Tuần vừa rồi",
  "nav.scorers": "Vua phá lưới",
  "common.back": "← Quay lại",
  "common.viewTx": "Xem giao dịch →",
  "common.season": "Mùa giải",
  "common.noData": "Chưa có dữ liệu.",
  "common.loading": "Đang tải…",

  // dashboard
  "dash.headline": "Trận đấu tuần này",
  "dash.subhead": "Dự đoán bằng Poisson + Dixon-Coles từ xG gần đây, phân tích bằng AI Qwen.",
  "dash.apiError": "Lỗi API",
  "dash.empty": "Chưa có trận nào sắp diễn ra. Chạy script ingest và predict.",
  "dash.stat.accuracy": "Độ chính xác",
  "dash.stat.baseline": "Baseline (đoán chủ nhà)",
  "dash.stat.logloss": "Log-loss",
  "dash.stat.matches": "Trận đã tính",

  // match card / status
  "status.scheduled": "Sắp diễn ra",
  "status.final": "Đã kết thúc",
  "status.live": "Đang đá",
  "match.topScore": "Tỷ số dự đoán",
  "match.liveScore": "Tỷ số trực tiếp",
  "match.finalScore": "Kết quả",
  "match.predictedLabel": "Dự đoán",
  "match.actualLabel": "Thực tế",
  "match.pending": "Chưa có dự đoán",
  "match.value": "Giá trị",
  "match.vs": "vs",

  // match detail
  "detail.breadcrumb": "Trận #{id} • {date} • {status}",
  "detail.expectedGoals": "Bàn thắng kỳ vọng (λ)",
  "detail.home": "Chủ",
  "detail.draw": "Hòa",
  "detail.away": "Khách",
  "detail.pendingPost": "Chưa có dự đoán — POST /api/predictions/{id}",
  "detail.analysis": "Phân tích",
  "detail.scoreMatrix.title": "Xác suất các tỷ số",
  "detail.scoreMatrix.top": "Dễ nhất",
  "detail.scoreMatrix.footer": "Mỗi ô là xác suất tỷ số đó xảy ra. Tính từ λ_chủ={lamH}, λ_khách={lamA}, ρ={rho}.",

  // fingerprint
  "fp.title": "Dấu vân tay dự đoán",
  "fp.badge": "xác minh được",
  "fp.explain": "SHA-256 cố định của nội dung dự đoán. Tự tính lại từ dữ liệu công khai để xác minh dự đoán không bị sửa sau trận.",

  // odds
  "odds.title": "Tỷ lệ cá cược",
  "odds.outcome": "Kết quả",
  "odds.odds": "Tỷ lệ",
  "odds.fair": "XS công bằng",
  "odds.edge": "Chênh lệch vs AI",
  "odds.valueHint": "Mô hình thấy giá trị {edge} ở kết quả {outcome}. Mô hình và thị trường có thể khác nhau — bạn tự quyết định.",

  // table
  "table.title": "Bảng xếp hạng theo xG",
  "table.subhead": "Điểm thật là kết quả đã xảy ra. xG diff là kết quả đáng ra nên xảy ra.",
  "table.empty": "Chưa có trận nào kết thúc trong mùa {season}.",
  "table.col.rank": "#",
  "table.col.team": "Đội",
  "table.col.played": "T",
  "table.col.wins": "TH",
  "table.col.draws": "H",
  "table.col.losses": "TB",
  "table.col.gf": "BT",
  "table.col.ga": "BB",
  "table.col.gd": "HS",
  "table.col.xgf": "xG+",
  "table.col.xga": "xG-",
  "table.col.xgd": "xGΔ",

  // stats
  "stats.title": "Hiệu chỉnh mô hình",
  "stats.subhead": "Mô hình có tự biết nó đang chắc chắn cỡ nào không? Bảng bên dưới cho thấy số nào đáng tin.",
  "stats.brier": "Brier score",
  "stats.bins.title": "Độ tin cậy theo nhóm",
  "stats.bins.hint": "Nếu mô hình nói thật, tỷ lệ đúng nên nằm trong khoảng dự đoán. Δ dương = mô hình khiêm tốn; Δ âm = mô hình tự tin thái quá.",
  "stats.bins.empty": "Chưa đủ trận để tính.",
  "stats.bins.bin": "Nhóm",
  "stats.bins.n": "Số trận",
  "stats.bins.pred": "Dự đoán",
  "stats.bins.actual": "Thực tế",
  "stats.bins.delta": "Δpp",
  "stats.bins.reliability": "Độ tin cậy",
  "stats.weekly.title": "Độ chính xác theo tuần",
  "stats.weekly.hint": "Đường baseline = luôn chọn chủ nhà = {baseline}. Cột cao hơn tức là mô hình đánh bại naive.",

  // team profile
  "team.played": "Đã đá",
  "team.record": "T-H-B",
  "team.points": "Điểm",
  "team.goals": "Bàn (BT–BB)",
  "team.xgDiff": "xG chênh lệch",
  "team.form": "Phong độ (10 trận gần nhất)",
  "team.form.none": "Chưa có trận nào kết thúc.",
  "team.topScorers": "Vua phá lưới",
  "team.topScorers.empty": "Chưa có dữ liệu cầu thủ. Chạy scripts/ingest_players.py --season {season}.",
  "team.recent": "Trận gần nhất",
  "team.upcoming": "Sắp tới",
  "team.none": "(chưa có)",
  "team.trajectoryTitle": "Đồ thị phong độ (xG trung bình 5 trận)",
  "team.trajectoryMatches": "trận",
  "team.trajectoryXgFor": "xG ghi {value}",
  "team.trajectoryXgAgainst": "xG thủng {value}",
  "team.trajectoryFooter": "Đường xanh = số bàn đội đáng ghi. Đường đỏ = số bàn đội đáng thủng. Giao nhau = bước ngoặt mùa.",

  // chat widget
  "chat.title": "Hỏi chuyên gia",
  "chat.placeholder": "Hỏi bất kỳ điều gì về trận này…",
  "chat.send": "Gửi",
  "chat.streaming": "Đang suy nghĩ…",
  "chat.empty": "Đặt câu hỏi về trận — hoặc chọn gợi ý bên dưới.",
  "chat.error": "Có lỗi xảy ra.",
  "chat.you": "Bạn",
  "chat.bot": "Chuyên gia",

  // recent window
  "recent.title": "Mô hình đoán tuần vừa rồi thế nào",
  "recent.subhead": "Các trận kết thúc trong {days} ngày gần nhất, kèm lựa chọn mô hình đưa ra trước trận và kết quả thật.",
  "recent.empty": "Chưa có trận nào kết thúc trong {days} ngày qua.",
  "recent.summary.scored": "Số trận",
  "recent.summary.accuracy": "Độ chính xác",
  "recent.summary.logloss": "Log-loss",
  "recent.summary.correct": "Đoán đúng",
  "recent.hit": "Đúng",
  "recent.miss": "Sai",
  "recent.predicted": "Mô hình chọn",
  "recent.actual": "Kết quả",

  // ROI chart
  "roi.title": "Lãi/lỗ từ cược giá trị",
  "roi.subhead": "Lợi nhuận tích lũy nếu đặt đều 1u mỗi khi mô hình thấy edge ≥ {threshold}pp trong mùa này.",
  "roi.totalBets": "Số vé",
  "roi.totalPnl": "P&L (đơn vị)",
  "roi.roi": "ROI",
  "roi.empty": "Chưa có vé nào đạt ngưỡng.",

  // quick picks
  "quick.title": "Giá trị cao nhất tuần này",
  "quick.empty": "Chưa có vé giá trị đậm tuần này.",
  "quick.edge": "Chênh lệch",

  // scorers
  "scorers.title": "Vua phá lưới {season}",
  "scorers.subhead": "Ai đang dẫn đầu cuộc đua ghi bàn — và xG model nói ai may mắn hơn sức mình.",
  "scorers.sortGoals": "Bàn",
  "scorers.sortXg": "xG",
  "scorers.sortAssists": "Kiến tạo",
  "scorers.sortDelta": "Bàn − xG",
  "scorers.empty": "Chưa có dữ liệu cầu thủ mùa {season}.",
  "events.title": "Diễn biến trận đấu",
  "events.goals": "Bàn thắng",
  "events.cards": "Thẻ phạt",
  "events.subs": "Thay người",

  // H2H panel
  "h2h.title": "{n} lần gặp gần nhất",
  "h2h.empty": "Chưa có lần gặp nào trong DB.",
  "h2h.homeWins": "{team} thắng",
  "h2h.awayWins": "{team} thắng",
  "h2h.draws": "Hòa",
};

export default vi;
