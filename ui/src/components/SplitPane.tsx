"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";

export interface SplitPaneProps {
  split?: "vertical" | "horizontal";
  minSize?: number;
  maxSize?: number;
  defaultSize?: number | string;
  size?: number;
  onChange?: (newSize: number) => void;
  onDragStarted?: () => void;
  onDragFinished?: (newSize: number) => void;
  className?: string;
  pane1ClassName?: string;
  pane2ClassName?: string;
  resizerClassName?: string;
  children: [React.ReactNode, React.ReactNode];
  allowResize?: boolean;
}

export const SplitPane: React.FC<SplitPaneProps> = ({
  split = "vertical",
  minSize = 280,
  maxSize,
  defaultSize = "50%",
  size: controlledSize,
  onChange,
  onDragStarted,
  onDragFinished,
  className = "",
  pane1ClassName = "",
  pane2ClassName = "",
  resizerClassName = "",
  children,
  allowResize = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [internalSize, setInternalSize] = useState<number | null>(null);

  useEffect(() => {
    if (controlledSize !== undefined) {
      setInternalSize(controlledSize);
      return;
    }
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const total = split === "vertical" ? rect.width : rect.height;

    if (typeof defaultSize === "string" && defaultSize.endsWith("%")) {
      const pct = parseFloat(defaultSize) / 100;
      setInternalSize(Math.round(total * pct));
    } else if (typeof defaultSize === "number") {
      setInternalSize(defaultSize);
    } else {
      setInternalSize(Math.round(total * 0.5));
    }
  }, [defaultSize, controlledSize, split]);

  const currentSize = controlledSize !== undefined ? controlledSize : internalSize;

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!allowResize) return;
    e.preventDefault();
    setIsDragging(true);
    onDragStarted?.();
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (!allowResize) return;
    setIsDragging(true);
    onDragStarted?.();
  };

  const handleDoubleClick = () => {
    if (!allowResize || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const total = split === "vertical" ? rect.width : rect.height;
    const half = Math.round(total / 2);
    setInternalSize(half);
    onChange?.(half);
    onDragFinished?.(half);
  };

  const handleMouseMove = useCallback(
    (clientX: number, clientY: number) => {
      if (!isDragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      let newSize: number;

      if (split === "vertical") {
        newSize = clientX - rect.left;
      } else {
        newSize = clientY - rect.top;
      }

      const total = split === "vertical" ? rect.width : rect.height;
      const effectiveMax = maxSize ?? total - 150;

      if (newSize < minSize) newSize = minSize;
      if (newSize > effectiveMax) newSize = effectiveMax;

      setInternalSize(newSize);
      onChange?.(newSize);
    },
    [isDragging, split, minSize, maxSize, onChange]
  );

  useEffect(() => {
    if (!isDragging) return;

    const onMouseMove = (e: MouseEvent) => {
      handleMouseMove(e.clientX, e.clientY);
    };
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches[0]) {
        handleMouseMove(e.touches[0].clientX, e.touches[0].clientY);
      }
    };
    const onEnd = () => {
      setIsDragging(false);
      if (currentSize !== null) {
        onDragFinished?.(currentSize);
      }
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("touchmove", onTouchMove);
    window.addEventListener("mouseup", onEnd);
    window.addEventListener("touchend", onEnd);

    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("mouseup", onEnd);
      window.removeEventListener("touchend", onEnd);
    };
  }, [isDragging, handleMouseMove, onDragFinished, currentSize]);

  const isVertical = split === "vertical";

  return (
    <div
      ref={containerRef}
      className={`relative flex w-full h-full overflow-hidden select-none ${
        isVertical ? "flex-row" : "flex-col"
      } ${className}`}
      style={{ userSelect: isDragging ? "none" : "auto" }}
    >
      <div
        className={`overflow-auto flex-shrink-0 relative ${pane1ClassName}`}
        style={{
          [isVertical ? "width" : "height"]:
            currentSize !== null ? `${currentSize}px` : defaultSize,
        }}
      >
        {children[0]}
      </div>

      <div
        role="separator"
        aria-orientation={split}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
        onDoubleClick={handleDoubleClick}
        title="Drag to resize / Double-click to reset (50/50)"
        className={`Resizer ${split} ${isDragging ? "active" : ""} ${
          !allowResize ? "disabled" : ""
        } ${resizerClassName} group flex items-center justify-center`}
      >
        <div
          className={`resizer-handle rounded-full bg-border-strong group-hover:bg-accent-brand group-hover:shadow-[0_0_8px_#38bdf8] transition-all ${
            isVertical ? "w-1 h-8 my-auto" : "h-1 w-8 mx-auto"
          } ${isDragging ? "!bg-accent-brand !h-12 shadow-[0_0_12px_#38bdf8]" : ""}`}
        />
      </div>

      <div className={`flex-1 overflow-auto relative ${pane2ClassName}`}>
        {children[1]}
      </div>

      {isDragging && (
        <div
          className="fixed inset-0 z-50"
          style={{ cursor: isVertical ? "col-resize" : "row-resize" }}
        />
      )}
    </div>
  );
};

export default SplitPane;
