// 商户数据存储 - 内存版 (原型演示用)
const queueStore = new Map();  // queue_number -> { service_id, table_type_id, people_count, status, created_at }
const bookingStore = new Map(); // booking_id -> { service_id, date, time, people_count, status, created_at }
const counterStore = new Map(); // service_id -> { queue_counter: number }

// 初始化计数器
counterStore.set('jin_001', { queue_counter: 30 });
counterStore.set('hong_001', { queue_counter: 20 });

function generateQueueNumber(serviceId) {
    const counter = counterStore.get(serviceId) || { queue_counter: 0 };
    counter.queue_counter++;
    counterStore.set(serviceId, counter);
    return `A${counter.queue_counter}`;
}

function generateBookingId() {
    return `B${Date.now()}`;
}

module.exports = {
    // 排队操作
    takeQueue: (serviceId, tableTypeId, peopleCount) => {
        const queueNumber = generateQueueNumber(serviceId);
        const record = {
            service_id: serviceId,
            table_type_id: tableTypeId,
            people_count: peopleCount,
            status: 'waiting',
            created_at: new Date().toISOString()
        };
        queueStore.set(queueNumber, record);
        return {
            queue_number: queueNumber,
            estimated_wait_minutes: Math.floor(Math.random() * 15) + 5,
            table_type: tableTypeId,
            status: 'success',
            message: '取号成功，请按时到店'
        };
    },
    
    getQueueList: (serviceId) => {
        const list = [];
        for (const [num, record] of queueStore) {
            if (record.service_id === serviceId && record.status === 'waiting') {
                list.push({
                    queue_number: num,
                    ...record
                });
            }
        }
        return list.sort((a, b) => a.created_at.localeCompare(b.created_at));
    },
    
    getQueueStatus: (serviceId) => {
        const waiting = queueStore.size > 0 ? 
            Array.from(queueStore.values()).filter(r => r.service_id === serviceId && r.status === 'waiting').length : 0;
        return {
            current_wait: waiting,
            avg_wait_minutes: waiting * 7
        };
    },
    
    cancelQueue: (queueNumber) => {
        const record = queueStore.get(queueNumber);
        if (record) {
            record.status = 'cancelled';
            return { status: 'success', message: '排队已取消' };
        }
        return { status: 'error', message: '排队号不存在' };
    },
    
    // 预约操作
    bookTable: (serviceId, date, time, peopleCount) => {
        const bookingId = generateBookingId();
        const record = {
            service_id: serviceId,
            date: date,
            time: time,
            people_count: peopleCount,
            status: 'confirmed',
            created_at: new Date().toISOString()
        };
        bookingStore.set(bookingId, record);
        return {
            booking_id: bookingId,
            date: date,
            time: time,
            people_count: peopleCount,
            status: 'confirmed',
            message: '预订成功'
        };
    },
    
    getBookingList: (serviceId) => {
        const list = [];
        for (const [id, record] of bookingStore) {
            if (record.service_id === serviceId) {
                list.push({
                    booking_id: id,
                    ...record
                });
            }
        }
        return list.sort((a, b) => a.created_at.localeCompare(b.created_at));
    },
    
    // 统计
    getStats: (serviceId) => {
        const queues = Array.from(queueStore.values()).filter(r => r.service_id === serviceId);
        const bookings = Array.from(bookingStore.values()).filter(r => r.service_id === serviceId);
        return {
            queue_waiting: queues.filter(q => q.status === 'waiting').length,
            queue_today: queues.length,
            booking_today: bookings.length,
            booking_confirmed: bookings.filter(b => b.status === 'confirmed').length
        };
    }
};
