"use client";
import React, { useRef } from "react";
import { Card } from "@/components/ui/card";
import DeviceSwitch from "./DeviceSwitch";
import {
	DndContext,
	closestCenter,
	useSensor,
	useSensors,
	PointerSensor,
	TouchSensor,
} from "@dnd-kit/core";
import { SortableContext, useSortable, arrayMove, rectSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

// 新定义设备类型
type DeviceType = "chosen" | "default";

interface Device {
	name: string;
	icon: any;
	status: boolean;
	type: DeviceType; // 新增设备类型字段
}

interface DraggableDevicesProps {
	devices: Device[];
	onDeviceStatusChange: (deviceName: string, newStatus: boolean) => void;
	onDevicesOrderChange: (newDevices: Device[]) => void;
}

const DraggableDevices: React.FC<DraggableDevicesProps> = ({ devices, onDeviceStatusChange, onDevicesOrderChange }) => {
	const sensors = useSensors(
		useSensor(PointerSensor, {
			activationConstraint: {
				delay: 300, // 长按300ms触发拖拽
				tolerance: 5,
			},
		}),
		useSensor(TouchSensor, {
			activationConstraint: {
				delay: 300, // 长按300ms触发拖拽
				tolerance: 5,
			},
		})
	);

	const handleDragEnd = (event: any) => {
		const { active, over } = event;
		if (active.id !== over.id) {
			const oldIndex = devices.findIndex((device) => device.name === active.id);
			const newIndex = devices.findIndex((device) => device.name === over.id);
			const newDevices = arrayMove(devices, oldIndex, newIndex);
			onDevicesOrderChange(newDevices); 
		}
	};

	return (
		<div>
			<h2 className="text-lg font-medium mb-4">快捷控制</h2>
			<DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd} sensors={sensors}>
				<SortableContext
					items={devices.map((device) => device.name)}
					strategy={rectSortingStrategy}
				>	{/* 新调整父容器的 Grid 布局 */}
					<div className="grid grid-cols-3 md:grid-cols-3 lg:grid-cols-3 gap-4 auto-rows-min items-start">
						{devices.map((device) => (
							<SortableDevice
								key={device.name}
								id={device.name}
								device={device}
								onStatusChange={(newStatus) =>
									onDeviceStatusChange(device.name, newStatus)
								}
							/>
						))}
					</div>
				</SortableContext>
			</DndContext>
		</div>
	);
};

interface SortableDeviceProps {
	id: string;
	device: Device;
	onStatusChange: (newStatus: boolean) => void;
}

const SortableDevice: React.FC<SortableDeviceProps> = ({ id, device, onStatusChange }) => {
	const switchRef = useRef<HTMLDivElement>(null);
	const {
		attributes,
		listeners,
		setNodeRef,
		transform,
		transition,
		isDragging
	} = useSortable({ id });

	// 检查点击是否发生在开关区域
	const isClickOnSwitch = (e: React.MouseEvent) => {
		if (!switchRef.current) return false;
		return switchRef.current.contains(e.target as Node);
	};

	// 新增判断类型的函数
	const getDeviceStyle = (type: DeviceType) => {
		const baseClasses = "hover:shadow-md transition-all duration-300 relative rounded-lg border cursor-grab min-h-[120px]";

		return type === "chosen"
			? `${baseClasses} p-30 bg-yellow-50 border-yellow-400 col-span-2 row-span-2 shadow-lg`
			: `${baseClasses} p-4 bg-white border-gray-200`;
	};

	return (
		<Card
			ref={setNodeRef}
			style={{
				transform: CSS.Transform.toString(transform),
				transition,
				cursor: 'grab', // 显示可拖拽的手型光标
				zIndex: isDragging ? 999 : 1
			}}
			{...attributes}
			className={getDeviceStyle(device.type)} // 新增根据类名修改格式
			{...listeners}
			onClick={(e) => {
				// 如果点击的是开关区域，阻止拖拽
				if (isClickOnSwitch(e)) {
					e.stopPropagation();
				}
			}}
		>
			<div ref={switchRef}>
				<DeviceSwitch device={device} onStatusChange={onStatusChange} />
			</div>
		</Card>
	);
};

export default DraggableDevices;    