import type { Tool } from './types';

export class DrawingCanvas {
  private ctx: CanvasRenderingContext2D;
  private drawing = false;
  private canvas: HTMLCanvasElement;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const dpr = window.devicePixelRatio || 1;
    canvas.style.width = '500px';
    canvas.style.height = '400px';
    canvas.width = 500 * dpr;
    canvas.height = 400 * dpr;
    this.ctx = canvas.getContext('2d')!;
    this.ctx.scale(dpr, dpr);
    this.ctx.fillStyle = '#ffffff';
    this.ctx.fillRect(0, 0, 500, 400);
    this.bindEvents();
  }

  setTool(tool: Tool): void {
    if (tool === 'pen') {
      this.ctx.globalCompositeOperation = 'source-over';
      this.ctx.strokeStyle = '#000000';
      this.ctx.lineWidth = 3;
    } else {
      this.ctx.globalCompositeOperation = 'destination-out';
      this.ctx.lineWidth = 15;
    }
    this.ctx.lineCap = 'round';
  }

  clear(): void {
    this.ctx.globalCompositeOperation = 'source-over';
    this.ctx.fillStyle = '#ffffff';
    this.ctx.fillRect(0, 0, 500, 400);
  }

  exportBase64(): string {
    return this.canvas.toDataURL('image/png');
  }

  private bindEvents(): void {
    this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
    this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
    this.canvas.addEventListener('mouseup', () => this.onMouseUp());
    this.canvas.addEventListener('mouseleave', () => this.onMouseUp());
  }

  private onMouseDown(e: MouseEvent): void {
    this.drawing = true;
    this.ctx.beginPath();
    const rect = this.canvas.getBoundingClientRect();
    this.ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
  }

  private onMouseMove(e: MouseEvent): void {
    if (!this.drawing) return;
    const rect = this.canvas.getBoundingClientRect();
    this.ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    this.ctx.stroke();
  }

  private onMouseUp(): void {
    if (this.drawing) {
      this.ctx.closePath();
      this.drawing = false;
    }
  }
}
