"use client";

import { useState, useEffect, useCallback, useRef } from "react";

export interface SelectionContext {
  selectedText: string;
  filePath: string;
  position: { top: number; left: number };
  range?: Range;
}

export function SelectionActionBar({
  containerRef,
  filePath,
  onAction,
}: {
  containerRef: React.RefObject<HTMLElement | null>;
  filePath: string;
  onAction: (context: SelectionContext) => void;
}) {
  const [show, setShow] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [selectedText, setSelectedText] = useState("");
  const barRef = useRef<HTMLDivElement>(null);

  const handleMouseUp = useCallback(() => {
    // Small delay to let selection finalize
    setTimeout(() => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !sel.toString().trim()) {
        setShow(false);
        return;
      }

      const text = sel.toString().trim();
      if (!text || !containerRef.current) return;

      // Check selection is within our container
      const range = sel.getRangeAt(0);
      if (!containerRef.current.contains(range.commonAncestorContainer)) {
        setShow(false);
        return;
      }

      const rect = range.getBoundingClientRect();
      setSelectedText(text);
      setPosition({
        top: rect.top - 44,
        left: rect.left + rect.width / 2,
      });
      setShow(true);
    }, 10);
  }, [containerRef]);

  const handleMouseDown = useCallback((e: MouseEvent) => {
    // Hide bar if clicking outside it
    if (barRef.current && !barRef.current.contains(e.target as Node)) {
      setShow(false);
    }
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("mousedown", handleMouseDown);
    return () => {
      container.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("mousedown", handleMouseDown);
    };
  }, [containerRef, handleMouseUp, handleMouseDown]);

  const handleClick = () => {
    const sel = window.getSelection();
    let pos = position;
    let range: Range | undefined;
    if (sel && !sel.isCollapsed) {
      range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      pos = { top: rect.bottom + 8, left: rect.left + rect.width / 2 };

      // Highlight the selected text with a yellow background
      try {
        const highlight = document.createElement("mark");
        highlight.className = "workany-highlight";
        highlight.style.cssText = "background: #FFF3BF; border-radius: 2px; padding: 0 1px;";
        range.surroundContents(highlight);
      } catch {
        // surroundContents fails if selection spans multiple elements — fallback
      }
    }
    onAction({
      selectedText,
      filePath,
      position: pos,
      range,
    });
    setShow(false);
  };

  if (!show) return null;

  return (
    <div
      ref={barRef}
      className="fixed z-50 flex items-center rounded-lg border border-border bg-background px-1 py-0.5 shadow-lg"
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`,
        transform: "translateX(-50%)",
      }}
    >
      <button
        onClick={handleClick}
        className="flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors hover:bg-accent-light hover:text-accent"
      >
        <span>💬</span>
        <span>Ask</span>
      </button>
    </div>
  );
}
