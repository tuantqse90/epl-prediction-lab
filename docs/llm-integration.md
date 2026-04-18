# LLM Integration

## Reasoning Generation (bulk, post-prediction)

**Model**: Qwen-Turbo (default) → Qwen-Plus for top-6 clashes.
**Trigger**: auto-generate right after each prediction is computed.

### Prompt template (Vietnamese peer-style)

```
Bạn là một nhà phân tích bóng đá sắc bén, nói chuyện kiểu anh em.
Không khoa trương. Dùng số liệu thật. Tối đa 3 câu.

Trận đấu: {home_team} vs {away_team}
Dự đoán của model (Poisson-based):
- Thắng sân nhà: {p_home:.0%}
- Hòa: {p_draw:.0%}
- Thua sân nhà: {p_away:.0%}
- Tỷ số dự đoán: {top_score}

Dữ liệu gần đây (5 trận):
- {home_team}: xG trung bình {home_xg_avg}, xGA {home_xga_avg}
- {away_team}: xG trung bình {away_xg_avg}, xGA {away_xga_avg}

H2H 3 trận gần nhất: {h2h_summary}

Giải thích ngắn gọn VÌ SAO model predict như vậy.
Chỉ rõ 2-3 số liệu quan trọng nhất.
```

## Chat Q&A (streaming)

**Model**: Qwen-Turbo. Streamed responses via Vercel AI SDK.

### RAG context builder

- Last 5 matches of both teams (xG, goals, opponent)
- Top 5 scorers of each team (season stats)
- H2H last 3 matches
- The prediction + reasoning from DB

### Prompt template

```
Bạn là AI analyst của EPL Lab. Nói tiếng Việt, giọng anh em, xưng "tao/mày".
Chỉ trả lời dựa trên DATA bên dưới. KHÔNG bịa số.
Nếu không có trong data, nói "tao không có số đó".

===== DATA =====
Match: {home} vs {away}, {date}
Prediction: H {p_h:.0%} / D {p_d:.0%} / A {p_a:.0%}
Model reasoning: {reasoning}

Home team last 5:
{home_recent_matches}

Away team last 5:
{away_recent_matches}

H2H last 3:
{h2h}

Top scorers:
{top_scorers}
===== END DATA =====

Câu hỏi của user: {question}
```

## LiteLLM config

```yaml
# config.yaml
model_list:
  - model_name: reasoning-primary
    litellm_params:
      model: dashscope/qwen-turbo
      api_key: os.environ/DASHSCOPE_API_KEY
  - model_name: reasoning-premium
    litellm_params:
      model: dashscope/qwen-plus
      api_key: os.environ/DASHSCOPE_API_KEY
  - model_name: reasoning-fallback
    litellm_params:
      model: anthropic/claude-haiku-4-5
      api_key: os.environ/ANTHROPIC_API_KEY

router_settings:
  fallbacks:
    - reasoning-primary: [reasoning-premium, reasoning-fallback]
```
