$(document).ready(function() {
    let currentDrop = null;
    let currentEmployee = null;
    let editMode = false;
    let editingElement = null;
    let currentDate = new Date();
    let assignments = {}; // Almacenar asignaciones por fecha
    let URL_LOAD = "/gestion/clients/timetable/load";
    let URL_ASSIGN = "/gestion/clients/timetable/assign";
    let URL_SAVE = "/gestion/clients/timetable/assign-save2";
    let URL_EDIT = "/gestion/clients/timetable/assign-edit";
    let URL_REMOVE = "/gestion/clients/timetable/assign-remove";

    const monthNames = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];

    // Obtener texto del estado
    /*function getStatusText(status) {
        const statusMap = {
            'asignado': '📋 Asignado',
            'confirmado': '✅ Confirmado',
            'pendiente': '⏳ Pendiente',
            'cancelado': '❌ Cancelado',
            'completado': '🎉 Completado'
        };
        return statusMap[status] || '📋 Asignado';
    }*/

    // Generar calendario
    function generateCalendar(client, year, month) {
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
            
            let cellHtml = `<div class="day-cell" data-client="${client}" data-date="${dateStr}" ${todayClass}>
                <div class="day-number">${day}</div>
                <div id="day-cell-${dateStr}"></div>
                </div>
            `;

            $('#calendarGrid').append(cellHtml);
        }

        // Reinicializar droppables
        initializeDroppables();
    }

    // Inicializar droppables
    function initializeDroppables() {
        $(".day-cell").droppable({
            accept: ".employee",
            hoverClass: "ui-droppable-hover",
            drop: function(event, ui) {
                currentDrop = $(this);
                currentEmployee = {"id": ui.draggable.data('id'), "name": ui.draggable.data('name'), "date": $(this).data("date")};
                ajaxGet(URL_ASSIGN, currentEmployee, "", "common-modal")
                //ajaxGet(ui.draggable.data('url'), currentEmployee, "", "common-modal")
            }
        });
    }

    function loadCalendar(){
        $(".day-cell").each(function(){
            let dateStr = $(this).data("date");
            let client = $(this).data("client");
            ajaxGet(URL_LOAD, {"client": client, "date": dateStr}, "day-cell-"+dateStr, "")
        });
    }

    function normalizeText(str) {
        return str.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    }

    // Hacer los empleados arrastrables
    $(".employee").draggable({
        revert: "invalid",
        helper: "clone",
        cursor: "move",
        zIndex: 1000
    });

    // Confirmar asignación
    $(document).on('click', '#confirmBtn', function(e) {
        let startTime = $('#startTime').val();
        let endTime = $('#endTime').val();
        let startPrev = $('#startPrev').val();
        let endPrev = $('#endPrev').val();
        let status = $('#status').val();
        let allDays = $('input[id="allDays"]:checked').val();
        let monday = $('#monday').is(":checked");
        let tuesday = $('#tuesday').is(":checked");
        let wednesday = $('#wednesday').is(":checked");
        let thursday = $('#thursday').is(":checked");
        let friday = $('#friday').is(":checked");
        let saturday = $('#saturday').is(":checked");
        let sunday = $('#sunday').is(":checked");
        let cover = $('#cover').is(":checked");

        let obj_id = $(this).data("obj_id");
        let timetable = $(this).data("timetable");
        let dateStr = $(this).data("date");
        let empName = $(this).data("name");
        
        datas = {
            "timetable":timetable,
            "obj_id":obj_id,
            "date":dateStr,
            "ini":startTime,
            "end":endTime,
            "ini_prev":startPrev,
            "end_prev":endPrev,
            "repeat":allDays,
            "monday":monday,
            "tuesday":tuesday,
            "wednesday":wednesday,
            "thursday":thursday,
            "friday":friday,
            "saturday":saturday,
            "sunday":sunday,
            "cover":cover,
            "status":status
        };
        ajaxGet(URL_SAVE, datas, "day-cell-"+dateStr, "");
        
        currentDrop = null;
        currentEmployee = null;
    });

    // Editar asignación al hacer clic
    $(document).on('click', '.assigned-employee', function(e) {
        if ($(e.target).hasClass('remove-btn')) {
            return;
        }
        
        let timetableId = $(this).data('timetable-id');
        ajaxGet(URL_EDIT, {"id": timetableId}, "", "common-modal")
        //ajaxGet("/gestion/clients/timetable/assign-edit", {"id": timetableId}, "", "common-modal")
    });


    // Eliminar asignación
    $(document).on('click', '.remove-btn', function(e) {
        e.stopPropagation();
        if (confirm("¿Esta seguro/a de que desea borrar este elemento?")){
            const assignment = $(this).closest('.assigned-employee');
            const timetableId = assignment.data('timetable-id');
            const dateStr = assignment.closest('.day-cell').data('date');
            ajaxGet(URL_REMOVE, {"id": timetableId}, "day-cell-"+dateStr, "")
            //ajaxGet("/gestion/clients/timetable/assign-remove", {"id": timetableId}, "day-cell-"+dateStr, "")
        }
    });

    // Navegación de meses
    $('#prevMonth').click(function() {
        currentDate.setMonth(currentDate.getMonth() - 1);
        generateCalendar($(this).data("client"), currentDate.getFullYear(), currentDate.getMonth());
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

    // Inicializar calendario
    //generateCalendar(currentDate.getFullYear(), currentDate.getMonth());

    $(document).on('click', '#btn-start', function(e) {
        currentDate = new Date();
        generateCalendar($(this).data("client"), currentDate.getFullYear(), currentDate.getMonth());
        loadCalendar();
    });

    $(document).on('click', '.btn-emp', function(e) {
        let val = $(this).data("id");
        let values = $('#btn-save').data('values');
        if ($(this).hasClass('active')) {
            values = values.filter(function(item) {return item !== val;});
            $('#btn-save').data('values', values)
            $(this).removeClass("active");
        } else{
            values.push(val);
            $('#btn-save').data('values', values)
            $(this).addClass("active");
        }
    });

    $(document).on('keyup', '#search-emp', function(e) {
        let val = $(this).val();
        $(".divEmp").each(function(){
            let text = normalizeText($(this).text());
            let val_norm = normalizeText(val);

            //if ($(this).html().toLowerCase().includes(val.toLowerCase()))
            if (text.includes(val_norm))
                $(this).show();
            else 
                $(this).hide();
        });
    });

    $(document).on('click', '#btn-ini-drop', function(e) {
        $(".employee").draggable({
            revert: "invalid",
            helper: "clone",
            cursor: "move",
            zIndex: 1000
        });
        initializeDroppables();
    });
});

