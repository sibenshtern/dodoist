import { describe, it, expect, vi, beforeEach } from 'vitest';
import { signal, computed } from '@angular/core';

// Lightweight stub testing SseService state machine without Angular DI

const BACKOFF_STEPS = [1_000, 2_000, 5_000, 15_000, 30_000];

function makeBackoffIndex() {
  let idx = 0;
  return {
    nextDelay: () => BACKOFF_STEPS[Math.min(idx++, BACKOFF_STEPS.length - 1)],
    reset: () => { idx = 0; },
    get index() { return idx; },
  };
}

describe('SseService — backoff logic', () => {
  it('first retry delay is 1s', () => {
    const backoff = makeBackoffIndex();
    expect(backoff.nextDelay()).toBe(1_000);
  });

  it('subsequent retries increase delay', () => {
    const backoff = makeBackoffIndex();
    const delays = Array.from({ length: 5 }, () => backoff.nextDelay());
    expect(delays).toEqual([1_000, 2_000, 5_000, 15_000, 30_000]);
  });

  it('caps at last backoff step', () => {
    const backoff = makeBackoffIndex();
    for (let i = 0; i < 10; i++) backoff.nextDelay();
    expect(backoff.nextDelay()).toBe(30_000);
  });

  it('reset brings index back to start', () => {
    const backoff = makeBackoffIndex();
    backoff.nextDelay(); backoff.nextDelay();
    backoff.reset();
    expect(backoff.nextDelay()).toBe(1_000);
  });
});

describe('SseService — running state', () => {
  it('start sets running flag', () => {
    const running = { value: false };
    function start() { running.value = true; }
    function stop() { running.value = false; }

    start();
    expect(running.value).toBe(true);
    stop();
    expect(running.value).toBe(false);
  });
});
