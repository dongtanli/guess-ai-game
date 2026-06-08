/** 前端契约类型定义（与 contracts.py 对应）。 */

/** 应用状态常量，前后端同源引用 */
export const AppState = {
  DRAWING: "drawing",
  GUESSING: "guessing",
  RESULT: "result",
  FEEDBACK_DONE: "feedback_done",
} as const;

export type AppState = (typeof AppState)[keyof typeof AppState];

/** GET /api/topic 响应 */
export interface TopicResponse {
  topic: string;
}

/** POST /api/guess 响应 */
export interface GuessResponse {
  guess: string;
  confidence: number;
  model: string;
}

/** POST /api/feedback 请求 */
export interface FeedbackRequest {
  user_says_correct: boolean;
}

/** POST /api/feedback 响应 */
export interface FeedbackResponse {
  scored: boolean;
  score: number;
}

/** GET /api/score 响应 */
export interface ScoreResponse {
  score: number;
}

/** 画板工具类型 */
export type Tool = "pen" | "eraser";
