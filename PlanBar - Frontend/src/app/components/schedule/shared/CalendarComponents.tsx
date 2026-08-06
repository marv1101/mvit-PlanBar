import React from 'react';
import { motion } from 'motion/react';
import { useDrag } from 'react-dnd';
import type { Employee, Shift } from '../../../types';
import { EMPLOYEE_ITEM_TYPE, BREAK_START_ITEM_TYPE, BREAK_END_ITEM_TYPE } from './CalendarUtils';
import type { EmployeeDragItem, BreakDragItem } from './CalendarUtils';

// Shared EmployeeCard component
export function EmployeeCard({ employee }: { employee: Employee }) {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: EMPLOYEE_ITEM_TYPE,
    item: { employeeId: employee.id } as EmployeeDragItem,
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }), [employee.id]);

  return (
    <motion.div
      ref={(node: HTMLDivElement | null) => { drag(node); }}
      layout
      animate={{
        opacity: isDragging ? 0.3 : 1,
        scale: isDragging ? 0.95 : 1,
      }}
      whileHover={{ scale: 1.03, y: -2, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 400, damping: 25 }}
      className="p-3 rounded-lg border-2 cursor-move"
      style={{
        backgroundColor: employee.color + '15',
        borderColor: employee.color + '40'
      }}
    >
      <div className="flex items-center gap-2">
        <div
          className="w-3 h-3 rounded-full flex-shrink-0"
          style={{ backgroundColor: employee.color }}
        />
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm truncate" style={{ color: employee.color }}>
            {employee.name}
          </div>
          <div className="text-xs text-gray-500 truncate">
            {employee.roles.length > 0 ? `${employee.roles.length} Rolle(n)` : 'Keine Rollen'}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// Shared BreakStartHandle component
export function BreakStartHandle({ shift, cursorClass = 'cursor-ns-resize' }: { shift: Shift; cursorClass?: string }) {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: BREAK_START_ITEM_TYPE,
    item: { shift, breakType: 'start' as const } as BreakDragItem,
    collect: (monitor) => ({ isDragging: monitor.isDragging() }),
  }), [shift]);

  return (
    <div
      ref={(node: HTMLDivElement | null) => { drag(node); }}
      className={`absolute top-0 left-0 right-0 h-2 ${cursorClass} hover:bg-blue-400/30 active:bg-blue-400/50 flex items-center justify-center z-20 group/break`}
      style={{ opacity: isDragging ? 0.5 : 1 }}
      onMouseDown={(e) => e.stopPropagation()}
      onTouchStart={(e) => e.stopPropagation()}
    >
      <div className="w-6 h-[2px] bg-gray-400 rounded opacity-0 group-hover/break:opacity-100 transition-opacity" />
    </div>
  );
}

// Shared BreakEndHandle component
export function BreakEndHandle({ shift, cursorClass = 'cursor-ns-resize' }: { shift: Shift; cursorClass?: string }) {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: BREAK_END_ITEM_TYPE,
    item: { shift, breakType: 'end' as const } as BreakDragItem,
    collect: (monitor) => ({ isDragging: monitor.isDragging() }),
  }), [shift]);

  return (
    <div
      ref={(node: HTMLDivElement | null) => { drag(node); }}
      className={`absolute bottom-0 left-0 right-0 h-2 ${cursorClass} hover:bg-blue-400/30 active:bg-blue-400/50 flex items-center justify-center z-20 group/break`}
      style={{ opacity: isDragging ? 0.5 : 1 }}
      onMouseDown={(e) => e.stopPropagation()}
      onTouchStart={(e) => e.stopPropagation()}
    >
      <div className="w-6 h-[2px] bg-gray-400 rounded opacity-0 group-hover/break:opacity-100 transition-opacity" />
    </div>
  );
}
