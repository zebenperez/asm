$(document).ready(function() {
    let currentDrop = null;
    let currentEmployee = null;
    let editMode = false;
    let editingElement = null;
    let currentDate = new Date();
    let assignments = {}; // Almacenar asignaciones por fecha
    let URL_LOAD = "/gestion/employees/timetable/load";

    const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

    // Generar calendario
    function generateCalendar(employee, year, month) {
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startingDayOfWeek = firstDay.getDay();
        const adjustedStart = startingDayOfWeek === 0 ? 6 : startingDayOfWeek - 1;

        $('#currentMonth').text(`${monthNames[month]} ${year}`);
        
        // Limpiar el calendario (excepto los encabezados)
        $('#calendarGrid .day-cell').remove();

        // Añadir celdas vacías al inicio
        for (let i = 0; i < adjustedStart; i++) {
            $('#calendarGrid').append('<div class="day-cell" style="background: #e9ecef; border: none;"></div>');
        }

        // Añadir días del mes
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
            const isToday = new Date().toDateString() === new Date(year, month, day).toDateString();
            const todayClass = isToday ? 'style="border-color: #3b693b; border-width: 3px;"' : '';
            
            let cellHtml = `<div class="day-cell" data-employee="${employee}" data-date="${dateStr}" ${todayClass}>
                <div class="day-number">${day}</div>
                <div id="day-cell-${dateStr}"></div>
                </div>
            `;

            $('#calendarGrid').append(cellHtml);
        }
    }

    function loadCalendar(){
        $(".day-cell").each(function(){
            let dateStr = $(this).data("date");
            let employee = $(this).data("employee");
            ajaxGet(URL_LOAD, {"employee": employee, "date": dateStr}, "day-cell-"+dateStr, "")
        });
    }

    function normalizeText(str) {
        return str.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    }

    // Navegación de meses
    $('#prevMonth').click(function() {
        currentDate.setMonth(currentDate.getMonth() - 1);
        generateCalendar($(this).data("employee"), currentDate.getFullYear(), currentDate.getMonth());
        loadCalendar();
    });

    $('#nextMonth').click(function() {
        currentDate.setMonth(currentDate.getMonth() + 1);
        generateCalendar($(this).data("client"), currentDate.getFullYear(), currentDate.getMonth());
        loadCalendar();
    });

    $('#todayBtn').click(function() {
        currentDate = new Date();
        generateCalendar($(this).data("client"), currentDate.getFullYear(), currentDate.getMonth());
    });

    $(document).on('click', '#btn-start', function(e) {
        currentDate = new Date();
        generateCalendar($(this).data("employee"), currentDate.getFullYear(), currentDate.getMonth());
        loadCalendar();
    });
});

