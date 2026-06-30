import type {
  TopicResponse,
  GuessResponse,
  FeedbackResponse,
  ScoreResponse,
} from './types';

const USE_MOCK = false;
const BASE = '/api';

export async function fetchTopic(): Promise<TopicResponse> {
  if (USE_MOCK) return { topic: '苹果' };
  const res = await fetch(`${BASE}/topic`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function submitGuess(imageB64: string): Promise<GuessResponse> {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 800));
    return { guess: '苹果', confidence: 0.92, model: 'mock-model' };
  }
  const res = await fetch(`${BASE}/guess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_b64: imageB64 }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function sendFeedback(
  userSaysCorrect: boolean,
): Promise<FeedbackResponse> {
  if (USE_MOCK) {
    const score = userSaysCorrect ? 1 : 0;
    return { scored: userSaysCorrect, score };
  }
  const res = await fetch(`${BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_says_correct: userSaysCorrect }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getScore(): Promise<ScoreResponse> {
  if (USE_MOCK) return { score: 0 };
  const res = await fetch(`${BASE}/score`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchReset(): Promise<{ ok: boolean }> {
  if (USE_MOCK) return { ok: true };
  const res = await fetch(`${BASE}/reset`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
