import React from "react";
import { useCurrentFrame } from "remotion";

/**
 * <TypeInText> — letter-by-letter type-in animation.
 *
 * @param text     Full text to reveal.
 * @param cps      Characters-per-second reveal rate (default 30 — readable but lively).
 * @param startAt  Frame within the parent sequence at which to begin (default 0).
 * @param style    Standard CSS (font, color, etc.).
 * @param showCaret Render a blinking caret at the leading edge while typing (default true).
 */
export const TypeInText: React.FC<{
  text: string;
  cps?: number;
  startAt?: number;
  style?: React.CSSProperties;
  showCaret?: boolean;
}> = ({ text, cps = 30, startAt = 0, style, showCaret = true }) => {
  const frame = useCurrentFrame();
  const elapsedFrames = Math.max(0, frame - startAt);
  // 30 fps × cps chars/sec = (30/cps) frames per char
  const framesPerChar = 30 / cps;
  const charsRevealed = Math.min(
    text.length,
    Math.floor(elapsedFrames / framesPerChar),
  );
  const visible = text.slice(0, charsRevealed);
  const isTyping = charsRevealed < text.length;
  // Blink the caret every 15 frames (~2 Hz)
  const caretVisible = Math.floor(frame / 15) % 2 === 0;

  return (
    <span style={style}>
      {visible}
      {showCaret && isTyping && caretVisible && (
        <span style={{ opacity: 0.7 }}>▌</span>
      )}
    </span>
  );
};
