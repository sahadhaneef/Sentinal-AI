import { useEffect, useRef } from 'react';
import { useLandingReducedMotion } from './LandingMotion';

/** A small procedural field of illuminated fibers and drifting data motes. */
export function CinematicField({ running, dark = false }: { running: boolean; dark?: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const reduce = useLandingReducedMotion();
  useEffect(() => {
    const element = canvas.current;
    const context = element?.getContext('2d');
    if (!element || !context) return;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0;
    let time = 0;
    let previous = 0;
    let width = 1;
    let height = 1;
    const draw = () => {
      context.clearRect(0, 0, width, height);
      const blue = dark ? '100,175,255' : '30,100,190';
      const teal = dark ? '92,231,214' : '12,130,140';
      // Curving fibers fan out from a luminous focus, with independent phases.
      for (let i = 0; i < 34; i++) {
        const phase = i * 0.37;
        const sway = Math.sin(time * 0.35 + phase) * height * 0.045;
        context.beginPath();
        context.moveTo(width * 1.12, height * (0.18 + i * 0.018));
        context.bezierCurveTo(width * 0.72, height * 0.38 + sway,
          width * 0.52, height * (0.1 + i * 0.026) - sway,
          -width * 0.12, height * (0.4 + i * 0.023));
        context.strokeStyle = `rgba(${i % 3 ? blue : teal},${dark ? 0.08 + (i % 5) * 0.015 : 0.045})`;
        context.lineWidth = i % 6 === 0 ? 1.3 : 0.65;
        context.stroke();
      }
      const count = width < 768 ? 30 : 80;
      for (let i = 0; i < count; i++) {
        const depth = 0.3 + (i % 7) / 9;
        const x = ((i * 127.7 + time * (12 + depth * 22)) % (width + 80)) - 40;
        const y = ((i * 83.3) % height) + Math.sin(time * 0.5 + i * 2.4) * 24;
        const alpha = (dark ? 0.25 : 0.12) + (Math.sin(time * 1.2 + i) + 1) * (dark ? 0.18 : 0.05);
        context.strokeStyle = `rgba(${i % 3 ? blue : teal},${alpha})`;
        context.lineWidth = depth * 1.4;
        context.beginPath();
        context.moveTo(x, y);
        context.lineTo(x + 3 + depth * 8, y - 2 - depth * 4);
        context.stroke();
        if (dark && i % 8 === 0) {
          const glow = context.createRadialGradient(x, y, 0, x, y, 12);
          glow.addColorStop(0, `rgba(${teal},0.22)`);
          glow.addColorStop(1, `rgba(${teal},0)`);
          context.fillStyle = glow;
          context.fillRect(x - 12, y - 12, 24, 24);
        }
      }
    };
    const tick = (now: number) => {
      if (now - previous >= 32) {
        time += Math.min(now - previous, 64) / 1000;
        previous = now;
        draw();
      }
      frame = requestAnimationFrame(tick);
    };
    const sync = () => {
      cancelAnimationFrame(frame);
      draw();
      if (running && !reduce && !media.matches) {
        previous = performance.now();
        frame = requestAnimationFrame(tick);
      }
    };
    const resize = () => {
      const bounds = element.getBoundingClientRect();
      width = bounds.width;
      height = bounds.height;
      const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
      element.width = Math.round(width * ratio);
      element.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      draw();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    resize();
    sync();
    media.addEventListener('change', sync);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      media.removeEventListener('change', sync);
    };
  }, [running, dark, reduce]);
  return <canvas ref={canvas} className={`cinematic-field${dark ? ' cinematic-field-dark' : ''}`} aria-hidden="true" />;
}
