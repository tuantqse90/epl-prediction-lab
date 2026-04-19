import type en from "./en";

const th: typeof en = {
  // global
  "site.title": "EPL Prediction Lab",
  "site.tagline": "xG ไม่โกหก แต่เจ้ามือโกหก",
  "nav.fixtures": "โปรแกรม",
  "nav.table": "ตารางคะแนน",
  "nav.stats": "สถิติ",
  "nav.recent": "สุดสัปดาห์ที่ผ่านมา",
  "nav.scorers": "ดาวซัลโว",
  "common.back": "← ย้อนกลับ",
  "common.viewTx": "ดูธุรกรรม →",
  "common.season": "ฤดูกาล",
  "common.noData": "ยังไม่มีข้อมูล",
  "common.loading": "กำลังโหลด…",

  // dashboard
  "dash.headline": "โปรแกรมสัปดาห์นี้",
  "dash.subhead": "Poisson + Dixon-Coles จาก xG ล่าสุด · วิเคราะห์โดย AI Qwen",
  "dash.apiError": "เกิดข้อผิดพลาด API",
  "dash.empty": "ยังไม่มีแมตช์ที่จะมาถึง รันสคริปต์ ingest และ predict",
  "dash.stat.accuracy": "ความแม่นยำของโมเดล",
  "dash.stat.baseline": "ฐาน (เจ้าบ้านเสมอ)",
  "dash.stat.logloss": "Log-loss",
  "dash.stat.matches": "จำนวนแมตช์ที่ให้คะแนน",

  // match card / status
  "status.scheduled": "กำลังจะมาถึง",
  "status.final": "จบเกม",
  "status.live": "สด",
  "match.topScore": "สกอร์ที่คาดการณ์",
  "match.liveScore": "สกอร์สด",
  "match.finalScore": "สกอร์สุดท้าย",
  "match.predictedLabel": "คาดการณ์",
  "match.actualLabel": "จริง",
  "match.pending": "รอการคาดการณ์",
  "match.value": "มูลค่า",
  "match.vs": "vs",

  // match detail
  "detail.breadcrumb": "แมตช์ #{id} • {date} • {status}",
  "detail.expectedGoals": "ประตูคาดหวัง (λ)",
  "detail.home": "เจ้าบ้าน",
  "detail.draw": "เสมอ",
  "detail.away": "ทีมเยือน",
  "detail.pendingPost": "ยังไม่มีคาดการณ์ — POST /api/predictions/{id}",
  "detail.analysis": "การวิเคราะห์",
  "detail.scoreMatrix.title": "ความน่าจะเป็นของสกอร์",
  "detail.scoreMatrix.top": "น่าจะเกิดขึ้นมากที่สุด",
  "detail.scoreMatrix.footer": "แต่ละช่องคือความน่าจะเป็นของสกอร์นั้น ๆ คำนวณจาก λ_home={lamH}, λ_away={lamA}, ρ={rho}",

  // fingerprint
  "fp.title": "ลายนิ้วมือการคาดการณ์",
  "fp.badge": "ตรวจสอบได้",
  "fp.explain": "SHA-256 แบบคงที่ของเนื้อหาคาดการณ์ คำนวณใหม่จากข้อมูลสาธารณะเพื่อยืนยันว่าไม่ถูกแก้หลังแมตช์",

  // odds
  "odds.title": "ราคาต่อรอง",
  "odds.outcome": "ผลลัพธ์",
  "odds.odds": "ราคา",
  "odds.fair": "ความน่าจะเป็นยุติธรรม",
  "odds.edge": "ส่วนต่าง vs โมเดล",
  "odds.valueHint": "โมเดลเห็นมูลค่า {edge} ที่ผลลัพธ์ {outcome} โมเดลและตลาดอาจไม่เห็นตรงกัน — ตัดสินใจเอง",

  // table
  "table.title": "ตารางคะแนนตาม xG",
  "table.subhead": "คะแนนจริงคือสิ่งที่เกิดขึ้น ส่วนต่าง xG คือสิ่งที่ควรจะเกิด",
  "table.empty": "ยังไม่มีแมตช์จบในฤดูกาล {season}",
  "table.col.rank": "#",
  "table.col.team": "ทีม",
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
  "stats.title": "การปรับเทียบโมเดล",
  "stats.subhead": "โมเดลรู้ไหมว่ามันมั่นใจแค่ไหน? ตารางด้านล่างบอกว่าตัวเลขไหนควรเชื่อ",
  "stats.brier": "Brier score",
  "stats.bins.title": "ความน่าเชื่อถือตามกลุ่ม",
  "stats.bins.hint": "หากโมเดลซื่อสัตย์ อัตราถูกควรอยู่ในช่วงคาดการณ์ Δ บวก = โมเดลถ่อมตัว · Δ ลบ = มั่นใจเกินไป",
  "stats.bins.empty": "ยังมีแมตช์ไม่พอคำนวณ",
  "stats.bins.bin": "กลุ่ม",
  "stats.bins.n": "แมตช์",
  "stats.bins.pred": "คาดการณ์",
  "stats.bins.actual": "จริง",
  "stats.bins.delta": "Δpp",
  "stats.bins.reliability": "ความน่าเชื่อถือ",
  "stats.weekly.title": "ความแม่นยำรายสัปดาห์",
  "stats.weekly.hint": "เส้นฐาน = เลือกเจ้าบ้านตลอด = {baseline} · เสามากกว่านั้นแสดงว่าชนะการเลือกเชิงตรรกะ",

  // team profile
  "team.played": "แข่งแล้ว",
  "team.record": "W-D-L",
  "team.points": "คะแนน",
  "team.goals": "ประตู (GF–GA)",
  "team.xgDiff": "ส่วนต่าง xG",
  "team.form": "ฟอร์ม (10 นัดล่าสุด)",
  "team.form.none": "ยังไม่มีแมตช์จบ",
  "team.topScorers": "ดาวซัลโว",
  "team.topScorers.empty": "ยังไม่มีสถิติผู้เล่น รัน scripts/ingest_players.py --season {season}",
  "team.recent": "แมตช์ล่าสุด",
  "team.upcoming": "แมตช์ที่จะมาถึง",
  "team.none": "(ไม่มี)",
  "team.trajectoryTitle": "กราฟฟอร์ม (xG เฉลี่ย 5 นัด)",
  "team.trajectoryMatches": "แมตช์",
  "team.trajectoryXgFor": "xG ทำ {value}",
  "team.trajectoryXgAgainst": "xG เสีย {value}",
  "team.trajectoryFooter": "เส้นเขียว = ประตูที่ควรทำได้ · เส้นแดง = ประตูที่ควรเสีย · ตัดกัน = จุดเปลี่ยนของฤดูกาล",

  // chat widget
  "chat.title": "ถามนักวิเคราะห์",
  "chat.placeholder": "ถามอะไรเกี่ยวกับแมตช์นี้ก็ได้…",
  "chat.send": "ส่ง",
  "chat.streaming": "กำลังคิด…",
  "chat.empty": "ถามคำถามเกี่ยวกับแมตช์ หรือเลือกคำแนะนำด้านล่าง",
  "chat.error": "มีบางอย่างผิดพลาด",
  "chat.you": "คุณ",
  "chat.bot": "นักวิเคราะห์",

  // recent window
  "recent.title": "โมเดลทำได้ดีแค่ไหนในสัปดาห์ที่ผ่านมา",
  "recent.subhead": "แมตช์ที่จบใน {days} วันที่ผ่านมา พร้อมสิ่งที่โมเดลเลือกก่อนเริ่มและผลจริง",
  "recent.empty": "ไม่มีแมตช์จบใน {days} วันที่ผ่านมา",
  "recent.summary.scored": "จำนวนแมตช์",
  "recent.summary.accuracy": "ความแม่นยำ",
  "recent.summary.logloss": "Log-loss",
  "recent.summary.correct": "ทายถูก",
  "recent.hit": "ถูก",
  "recent.miss": "ผิด",
  "recent.predicted": "โมเดลเลือก",
  "recent.actual": "ผล",

  // ROI
  "roi.title": "กำไร/ขาดทุนจากเดิมพันเชิงมูลค่า",
  "roi.subhead": "กำไรสะสมหาก flat-stake 1 หน่วยทุกครั้งที่ส่วนต่างของโมเดล ≥ {threshold}pp ในฤดูกาลนี้",
  "roi.totalBets": "เดิมพัน",
  "roi.totalPnl": "P&L (หน่วย)",
  "roi.roi": "ROI",
  "roi.empty": "ยังไม่มีเดิมพันถึงเกณฑ์",

  // quick picks
  "quick.title": "มูลค่าสูงสุดสัปดาห์นี้",
  "quick.empty": "ไม่มีเดิมพันเชิงมูลค่าสัปดาห์นี้",
  "quick.edge": "ส่วนต่าง",

  // scorers
  "scorers.title": "ดาวซัลโว {season}",
  "scorers.subhead": "ใครกำลังนำการแข่งขันยิงประตู — และโมเดล xG บอกว่าใครโชคดี",
  "scorers.sortGoals": "ประตู",
  "scorers.sortXg": "xG",
  "scorers.sortAssists": "แอสซิสต์",
  "scorers.sortDelta": "ประตู − xG",
  "scorers.empty": "ยังไม่มีสถิติผู้เล่นในฤดูกาล {season}",
  "events.title": "สิ่งที่เกิดขึ้น",
  "events.goals": "ประตู",
  "events.cards": "ใบเตือน",
  "events.subs": "เปลี่ยนตัว",

  // H2H
  "h2h.title": "{n} นัดที่เจอกันล่าสุด",
  "h2h.empty": "ยังไม่มีนัดเคยเจอกันในฐานข้อมูล",
  "h2h.homeWins": "{team} ชนะ",
  "h2h.awayWins": "{team} ชนะ",
  "h2h.draws": "เสมอ",
};

export default th;
