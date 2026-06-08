import { AppState } from './types';
import type { Tool } from './types';
import { fetchTopic, submitGuess, sendFeedback } from './api';
import { DrawingCanvas } from './canvas';
import './style.css';

let appState: AppState = AppState.DRAWING;
let currentScore = 0;
let canvas: DrawingCanvas;
let currentTool: Tool = 'pen';

let elTopic: HTMLElement;
let elScore: HTMLElement;
let elLoading: HTMLElement;
let elResult: HTMLElement;
let elError: HTMLElement;
let btnClear: HTMLButtonElement;
let btnEraser: HTMLButtonElement;
let btnSubmit: HTMLButtonElement;
let btnNext: HTMLButtonElement;
let btnYes: HTMLButtonElement;
let btnNo: HTMLButtonElement;
let feedbackButtons: HTMLElement;

function renderUI(): void {
  const app = document.querySelector<HTMLDivElement>('#app')!;
  app.innerHTML = `
    <header id="topic-area">
      <span id="topic-text">加载中…</span>
      <span id="score-text">得分：0</span>
    </header>
    <div id="canvas-wrapper">
      <canvas id="drawing-canvas"></canvas>
    </div>
    <div id="toolbar">
      <button id="btn-clear">清空</button>
      <button id="btn-eraser">橡皮擦</button>
      <button id="btn-submit">提交猜画</button>
      <button id="btn-next" disabled>下一轮</button>
    </div>
    <div id="result-area">
      <div id="loading-text" class="hidden">AI 推断中…</div>
      <div id="guess-result" class="hidden"></div>
      <div id="feedback-buttons" class="hidden">
        <button id="btn-yes">✅ 猜对了</button>
        <button id="btn-no">❌ 猜错了</button>
      </div>
      <div id="error-text" class="hidden"></div>
    </div>
  `;
}

function grabElements(): void {
  elTopic = document.querySelector<HTMLElement>('#topic-text')!;
  elScore = document.querySelector<HTMLElement>('#score-text')!;
  elLoading = document.querySelector<HTMLElement>('#loading-text')!;
  elResult = document.querySelector<HTMLElement>('#guess-result')!;
  elError = document.querySelector<HTMLElement>('#error-text')!;
  btnClear = document.querySelector<HTMLButtonElement>('#btn-clear')!;
  btnEraser = document.querySelector<HTMLButtonElement>('#btn-eraser')!;
  btnSubmit = document.querySelector<HTMLButtonElement>('#btn-submit')!;
  btnNext = document.querySelector<HTMLButtonElement>('#btn-next')!;
  btnYes = document.querySelector<HTMLButtonElement>('#btn-yes')!;
  btnNo = document.querySelector<HTMLButtonElement>('#btn-no')!;
  feedbackButtons = document.querySelector<HTMLElement>('#feedback-buttons')!;
}

function setState(state: AppState): void {
  if (appState === state) return;
  appState = state;
  const drawing = state === AppState.DRAWING;
  const guessing = state === AppState.GUESSING;
  const result = state === AppState.RESULT;
  const done = state === AppState.FEEDBACK_DONE;

  btnClear.disabled = !drawing;
  btnEraser.disabled = !drawing;
  btnSubmit.disabled = !drawing;
  btnNext.disabled = !done;
  btnYes.disabled = !result;
  btnNo.disabled = !result;

  elLoading.classList.toggle('hidden', !guessing);
  elResult.classList.toggle('hidden', !result);
  feedbackButtons.classList.toggle('hidden', !result);
  elError.classList.add('hidden');
}

function showError(msg: string): void {
  elError.textContent = msg;
  elError.classList.remove('hidden');
}

async function loadTopic(): Promise<void> {
  try {
    const { topic } = await fetchTopic();
    elTopic.textContent = `请画：${topic}`;
  } catch {
    showError('网络错误，无法加载题目，请刷新页面重试');
    elTopic.textContent = '加载失败';
  }
}

async function handleSubmit(): Promise<void> {
  setState(AppState.GUESSING);
  const b64 = canvas.exportBase64();
  try {
    const result = await submitGuess(b64);
    if (result.guess === 'timeout') {
      elResult.textContent = 'AI 推断超时，请简化图画后重试';
    } else if (result.guess === 'error') {
      elResult.textContent = 'AI 服务异常，请稍后重试';
    } else {
      elResult.textContent = `AI 猜：${result.guess}`;
    }
    setState(AppState.RESULT);
  } catch {
    showError('网络错误，请重试');
    setState(AppState.DRAWING);
  }
}

async function handleFeedback(userSaysCorrect: boolean): Promise<void> {
  try {
    const res = await sendFeedback(userSaysCorrect);
    currentScore = res.score;
    elScore.textContent = `得分：${currentScore}`;
    setState(AppState.FEEDBACK_DONE);
  } catch {
    showError('网络错误，反馈提交失败');
    setState(AppState.FEEDBACK_DONE);
  }
}

async function handleNextRound(): Promise<void> {
  canvas.clear();
  elResult.textContent = '';
  elResult.classList.add('hidden');
  setState(AppState.DRAWING);
  await loadTopic();
}

function bindEvents(): void {
  btnClear.addEventListener('click', () => canvas.clear());
  btnEraser.addEventListener('click', () => {
    if (currentTool === 'pen') {
      currentTool = 'eraser';
      canvas.setTool('eraser');
      btnEraser.textContent = '画笔';
    } else {
      currentTool = 'pen';
      canvas.setTool('pen');
      btnEraser.textContent = '橡皮擦';
    }
  });
  btnSubmit.addEventListener('click', () => handleSubmit());
  btnNext.addEventListener('click', () => handleNextRound());
  btnYes.addEventListener('click', () => handleFeedback(true));
  btnNo.addEventListener('click', () => handleFeedback(false));
}

document.addEventListener('DOMContentLoaded', () => {
  renderUI();
  grabElements();

  const canvasEl = document.querySelector<HTMLCanvasElement>('#drawing-canvas')!;
  canvas = new DrawingCanvas(canvasEl);
  canvas.setTool('pen');

  setState(AppState.DRAWING);
  loadTopic();
  bindEvents();
});
