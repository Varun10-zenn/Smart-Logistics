import React, { useState, useRef } from 'react';
import type { NodeRead, EdgeRead, StorageLocationRead } from '../types/api';

interface WarehouseGraphCanvasProps {
  nodes: NodeRead[];
  edges: EdgeRead[];
  locations: StorageLocationRead[];
  selectedNodeId?: number | null;
  selectedEdgeId?: number | null;
  highlightNodeIds?: number[];
  pickRouteNodeIds?: number[];
  connectMode?: boolean;
  connectSourceNodeId?: number | null;
  onNodeClick?: (node: NodeRead) => void;
  onNodeDragEnd?: (nodeId: number, x: number, y: number) => void;
  onCanvasClick?: (x: number, y: number) => void;
  onEdgeClick?: (edge: EdgeRead) => void;
  readOnly?: boolean;
}

export function WarehouseGraphCanvas({
  nodes,
  edges,
  locations,
  selectedNodeId,
  selectedEdgeId,
  highlightNodeIds = [],
  pickRouteNodeIds = [],
  connectMode = false,
  connectSourceNodeId = null,
  onNodeClick,
  onNodeDragEnd,
  onCanvasClick,
  onEdgeClick,
  readOnly = false,
}: WarehouseGraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [draggingNodeId, setDraggingNodeId] = useState<number | null>(null);
  const [dragPos, setDragPos] = useState<{ x: number; y: number } | null>(null);

  // Bounds for canvas scaling (default 100x100 grid space mapped to canvas pixels)
  const CANVAS_WIDTH = 800;
  const CANVAS_HEIGHT = 500;
  const PADDING = 40;

  // Compute bounding box from nodes or default
  const maxX = Math.max(...nodes.map((n) => n.x_coord), 50);
  const maxY = Math.max(...nodes.map((n) => n.y_coord), 50);

  const scaleX = (CANVAS_WIDTH - PADDING * 2) / (maxX || 50);
  const scaleY = (CANVAS_HEIGHT - PADDING * 2) / (maxY || 50);

  const toScreenX = (x: number) => PADDING + x * scaleX;
  const toScreenY = (y: number) => PADDING + y * scaleY;

  const toGridX = (screenX: number) => Math.max(0, Math.round(((screenX - PADDING) / scaleX) * 10) / 10);
  const toGridY = (screenY: number) => Math.max(0, Math.round(((screenY - PADDING) / scaleY) * 10) / 10);

  const handlePointerDownNode = (e: React.PointerEvent, node: NodeRead) => {
    e.stopPropagation();
    if (readOnly) return;
    setDraggingNodeId(node.id);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMoveCanvas = (e: React.PointerEvent) => {
    if (draggingNodeId === null || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;
    setDragPos({ x: toGridX(screenX), y: toGridY(screenY) });
  };

  const handlePointerUpCanvas = (_e: React.PointerEvent) => {
    if (draggingNodeId !== null) {
      if (dragPos && onNodeDragEnd) {
        onNodeDragEnd(draggingNodeId, dragPos.x, dragPos.y);
      }
      setDraggingNodeId(null);
      setDragPos(null);
    }
  };

  const handleCanvasClickInternal = (e: React.MouseEvent) => {
    if (draggingNodeId !== null || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const screenX = e.clientX - rect.left;
    const screenY = e.clientY - rect.top;
    const gx = toGridX(screenX);
    const gy = toGridY(screenY);
    if (onCanvasClick) {
      onCanvasClick(gx, gy);
    }
  };

  // Location counts per node
  const locationCountsByNode: Record<number, number> = {};
  locations.forEach((loc) => {
    locationCountsByNode[loc.node_id] = (locationCountsByNode[loc.node_id] || 0) + 1;
  });

  return (
    <div className="relative w-full overflow-hidden bg-[#0A0D14] border border-slate-800 rounded-xl select-none">
      {/* Canvas Header Legend */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-slate-900/90 border-b border-slate-800 text-xs text-slate-300">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-emerald-500 border border-emerald-400" />
            <span className="font-semibold text-emerald-400">Depot</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-indigo-500 border border-indigo-400" />
            <span>Standard Node</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-red-500/80 border border-red-400" />
            <span>Blocked</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-full bg-amber-400 animate-pulse" />
            <span>Pick Route Path</span>
          </div>
        </div>

        <div className="text-[11px] text-slate-400">
          {connectMode ? (
            <span className="text-sky-400 font-medium animate-pulse">
              Connect Mode Active: Click a second node to connect edge
            </span>
          ) : (
            <span>Click empty space to add node • Drag to move</span>
          )}
        </div>
      </div>

      {/* SVG Canvas Workspace */}
      <div
        ref={containerRef}
        onClick={handleCanvasClickInternal}
        onPointerMove={handlePointerMoveCanvas}
        onPointerUp={handlePointerUpCanvas}
        className="relative w-full h-[480px] cursor-crosshair overflow-hidden"
      >
        <svg className="w-full h-full" viewBox={`0 0 ${CANVAS_WIDTH} ${CANVAS_HEIGHT}`}>
          {/* Grid Background Lines */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E293B" strokeWidth="0.8" opacity="0.6" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Render Edges */}
          {edges.map((edge) => {
            const fromNode = nodes.find((n) => n.id === edge.from_node_id);
            const toNode = nodes.find((n) => n.id === edge.to_node_id);
            if (!fromNode || !toNode) return null;

            const x1 = toScreenX(fromNode.id === draggingNodeId && dragPos ? dragPos.x : fromNode.x_coord);
            const y1 = toScreenY(fromNode.id === draggingNodeId && dragPos ? dragPos.y : fromNode.y_coord);
            const x2 = toScreenX(toNode.id === draggingNodeId && dragPos ? dragPos.x : toNode.x_coord);
            const y2 = toScreenY(toNode.id === draggingNodeId && dragPos ? dragPos.y : toNode.y_coord);

            const isSelected = selectedEdgeId === edge.id;
            const isBlocked = edge.is_blocked || fromNode.is_blocked || toNode.is_blocked;

            return (
              <g key={edge.id} className="cursor-pointer" onClick={(e) => { e.stopPropagation(); onEdgeClick?.(edge); }}>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={isBlocked ? '#EF4444' : isSelected ? '#38BDF8' : '#475569'}
                  strokeWidth={isSelected ? 3.5 : 2}
                  strokeDasharray={isBlocked ? '4 4' : undefined}
                  opacity={0.8}
                />
                {/* Midpoint distance badge */}
                <rect
                  x={(x1 + x2) / 2 - 14}
                  y={(y1 + y2) / 2 - 9}
                  width="28"
                  height="18"
                  rx="4"
                  fill="#0F172A"
                  stroke={isSelected ? '#38BDF8' : '#334155'}
                  strokeWidth="1"
                />
                <text
                  x={(x1 + x2) / 2}
                  y={(y1 + y2) / 2 + 3}
                  fill="#94A3B8"
                  fontSize="10"
                  textAnchor="middle"
                  fontFamily="sans-serif"
                >
                  {edge.distance_meters}m
                </text>
              </g>
            );
          })}

          {/* Render Pick Route Sequential Sequence Path */}
          {pickRouteNodeIds.length > 1 &&
            pickRouteNodeIds.map((nodeId, idx) => {
              if (idx === 0) return null;
              const prevNode = nodes.find((n) => n.id === pickRouteNodeIds[idx - 1]);
              const currNode = nodes.find((n) => n.id === nodeId);
              if (!prevNode || !currNode) return null;

              const x1 = toScreenX(prevNode.x_coord);
              const y1 = toScreenY(prevNode.y_coord);
              const x2 = toScreenX(currNode.x_coord);
              const y2 = toScreenY(currNode.y_coord);

              return (
                <line
                  key={`pick-path-${idx}`}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="#F59E0B"
                  strokeWidth="4"
                  strokeDasharray="6 4"
                  opacity="0.9"
                />
              );
            })}

          {/* Render Nodes */}
          {nodes.map((node) => {
            const isDragging = node.id === draggingNodeId;
            const x = toScreenX(isDragging && dragPos ? dragPos.x : node.x_coord);
            const y = toScreenY(isDragging && dragPos ? dragPos.y : node.y_coord);

            const isSelected = selectedNodeId === node.id;
            const isConnectSource = connectSourceNodeId === node.id;
            const isHighlighted = highlightNodeIds.includes(node.id);
            const locCount = locationCountsByNode[node.id] || 0;

            let fillColor = '#6366F1'; // Default Indigo
            let strokeColor = '#818CF8';

            if (node.is_depot) {
              fillColor = '#10B981'; // Emerald Green Depot
              strokeColor = '#34D399';
            } else if (node.is_blocked) {
              fillColor = '#EF4444'; // Red Blocked
              strokeColor = '#F87171';
            }

            if (isSelected || isConnectSource) {
              strokeColor = '#38BDF8';
            }

            return (
              <g
                key={node.id}
                className="cursor-grab active:cursor-grabbing transition-transform"
                onClick={(e) => { e.stopPropagation(); onNodeClick?.(node); }}
                onPointerDown={(e) => handlePointerDownNode(e, node)}
              >
                {/* Selection / Highlight Pulse Ring */}
                {(isSelected || isHighlighted || isConnectSource) && (
                  <circle
                    cx={x}
                    cy={y}
                    r="24"
                    fill="none"
                    stroke={isHighlighted ? '#EF4444' : '#38BDF8'}
                    strokeWidth="2.5"
                    strokeDasharray="3 3"
                    className="animate-spin"
                  />
                )}

                {/* Node Outer Circle */}
                <circle
                  cx={x}
                  cy={y}
                  r="16"
                  fill={fillColor}
                  stroke={strokeColor}
                  strokeWidth={isSelected ? '3' : '2'}
                />

                {/* Depot Icon / Indicator */}
                {node.is_depot && (
                  <text x={x} y={y + 4} fill="#FFFFFF" fontSize="12" textAnchor="middle" fontWeight="bold">
                    ★
                  </text>
                )}

                {!node.is_depot && (
                  <text x={x} y={y + 4} fill="#FFFFFF" fontSize="10" textAnchor="middle" fontWeight="bold">
                    {node.node_code.slice(-3)}
                  </text>
                )}

                {/* Storage Locations Count Badge */}
                {locCount > 0 && (
                  <g transform={`translate(${x + 10}, ${y - 12})`}>
                    <circle r="8" fill="#3B82F6" stroke="#FFFFFF" strokeWidth="1.5" />
                    <text x="0" y="3" fill="#FFFFFF" fontSize="9" textAnchor="middle" fontWeight="bold">
                      {locCount}
                    </text>
                  </g>
                )}

                {/* Node Code Label */}
                <text
                  x={x}
                  y={y + 28}
                  fill={node.is_depot ? '#34D399' : '#CBD5E1'}
                  fontSize="11"
                  fontWeight={node.is_depot ? 'bold' : 'normal'}
                  textAnchor="middle"
                >
                  {node.node_code} {node.is_depot ? '(DEPOT)' : ''}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
