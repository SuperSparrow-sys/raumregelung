(function(){
'use strict';

let sensorChart = null;
let sensorAktKey = '';

const SENSOR_MAP = {
  sensor_1: { nr:'Sensor 1', name:'Sensor 1', kanal:'temp_1', farbe:'#ef4444', box:'sensor1', valId:'valSensor1' },
  sensor_2: { nr:'Sensor 2', name:'Sensor 2', kanal:'temp_2', farbe:'#d97706', box:'sensor2', valId:'valSensor2' },
  sensor_3: { nr:'Sensor 3', name:'Sensor 3', kanal:'temp_3', farbe:'#3b82f6', box:'sensor3', valId:'valSensor3' },
  sensor_4: { nr:'Sensor 4', name:'Sensor 4', kanal:'temp_4', farbe:'#16a34a', box:'sensor4', valId:'valSensor4' },
};

function fmtDT(d) {
  var y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), day=String(d.getDate()).padStart(2,'0');
  var h=String(d.getHours()).padStart(2,'0'), min=String(d.getMinutes()).padStart(2,'0');
  return y+'-'+m+'-'+day+' '+h+':'+min;
}

function updateLinePositions() {
  var rect = document.getElementById('visuRechteck');
  if (!rect) return;
  var rel = rect.getBoundingClientRect();
  var s1 = document.getElementById('sensor1');
  var s2 = document.getElementById('sensor2');
  var s3 = document.getElementById('sensor3');
  var s4 = document.getElementById('sensor4');
  var evm = document.getElementById('ventilBox');
  if (!s1||!s2||!s3||!s4||!evm) return;
  var r1=s1.getBoundingClientRect(), r2=s2.getBoundingClientRect();
  var r3=s3.getBoundingClientRect(), r4=s4.getBoundingClientRect();
  var rv=evm.getBoundingClientRect();
  var cx = rv.left - rel.left + rv.width/2;
  var cy = rv.top  - rel.top  + rv.height/2;
  var lines = document.querySelectorAll('#visuLines line');
  var pts = [
    [r1.left-rel.left+r1.width/2, r1.top-rel.top+r1.height/2],
    [r2.left-rel.left+r2.width/2, r2.top-rel.top+r2.height/2],
    [r3.left-rel.left+r3.width/2, r3.top-rel.top+r3.height/2],
    [r4.left-rel.left+r4.width/2, r4.top-rel.top+r4.height/2],
  ];
  lines.forEach(function(line,i){
    if (i<4) {
      line.setAttribute('x1',cx); line.setAttribute('y1',cy);
      line.setAttribute('x2',pts[i][0]); line.setAttribute('y2',pts[i][1]);
    }
  });
}

function updateData() {
  fetch('/api/daten').then(function(r){return r.json();}).then(function(d){
    document.getElementById('valSensor1').textContent = d.sensor_1 != null ? d.sensor_1.toFixed(1) : '--';
    document.getElementById('valSensor2').textContent = d.sensor_2 != null ? d.sensor_2.toFixed(1) : '--';
    document.getElementById('valSensor3').textContent = d.sensor_3 != null ? d.sensor_3.toFixed(1) : '--';
    document.getElementById('valSensor4').textContent = d.sensor_4 != null ? d.sensor_4.toFixed(1) : '--';
    document.getElementById('valMittel').textContent = d.mittelwert != null ? d.mittelwert.toFixed(1) : '--';
    document.getElementById('valSoll').textContent = d.sollwert != null ? d.sollwert.toFixed(1) : '--';
    document.getElementById('valPid').textContent = d.pid_ausgabe != null ? Math.round(d.pid_ausgabe) : '--';
    var sollAnzeige = (d.hand_modus === true && d.hand_stellwert != null)
      ? Math.round(d.hand_stellwert)
      : (d.pid_ausgabe != null ? Math.round(d.pid_ausgabe) : '--');
    document.getElementById('valVentilIst').textContent = d.ventil_position != null ? Math.round(d.ventil_position) : '--';
    document.getElementById('valVentilSoll').textContent = sollAnzeige;

    // Hand-Modus UI aktualisieren
    var handModus = d.hand_modus === true;
    var modeBadge    = document.getElementById('modeBadge');
    var handRow      = document.getElementById('handControlRow');
    var handInput    = document.getElementById('handStellung');
    var ventilLabel  = document.getElementById('ventilLabel');
    if (modeBadge) {
      if (handModus) {
        modeBadge.textContent = 'HAND';
        modeBadge.className = 'mode-badge mode-hand';
        handRow.classList.add('aktiv');
        document.getElementById('ventilBox').classList.add('hand-aktiv');
        ventilLabel.textContent = 'Ventil \u2013 HAND';
        if (document.activeElement !== handInput) handInput.value = Math.round(d.hand_stellwert != null ? d.hand_stellwert : 0);
      } else {
        modeBadge.textContent = 'AUTO';
        modeBadge.className = 'mode-badge mode-auto';
        handRow.classList.remove('aktiv');
        document.getElementById('ventilBox').classList.remove('hand-aktiv');
        ventilLabel.textContent = 'Ventilantrieb';
      }
    }

    var kpEl = document.getElementById('kpInput');
    var kiEl = document.getElementById('kiInput');
    var kdEl = document.getElementById('kdInput');
    var sollEl = document.getElementById('sollInput');
    if (kpEl  && document.activeElement !== kpEl)  kpEl.value  = d.Kp;
    if (kiEl  && document.activeElement !== kiEl)  kiEl.value  = d.Ki;
    if (kdEl  && document.activeElement !== kdEl)  kdEl.value  = d.Kd;
    if (sollEl && document.activeElement !== sollEl) sollEl.value = d.sollwert;

    var badge = document.getElementById('alarmBadge');
    if (badge) {
      var count = d.alarm_count || 0;
      badge.textContent = count;
      badge.style.display = count > 0 ? 'flex' : 'none';
    }
  }).catch(function(){});
}

function loadSensorChart(key, stunden) {
  var info = SENSOR_MAP[key];
  if (!info) return;
  sensorAktKey = key;
  var jetzt = new Date();
  var von = new Date(jetzt.getTime() - stunden*3600000);

  document.getElementById('sensorModalTitel').textContent = info.name + ' – Verlauf';
  var detailDiv = document.getElementById('sensorDetailInfo');

  fetch('/api/historie?kanal='+info.kanal+'&von='+fmtDT(von)+'&bis='+fmtDT(jetzt))
    .then(function(r){return r.json();}).then(function(res){
      var daten = res.daten || [];
      var canvas = document.getElementById('sensorChartCanvas');
      canvas.style.display = '';
      var altMsg = canvas.parentElement.querySelector('.no-data-msg');
      if (altMsg) altMsg.remove();
      var ctx = canvas.getContext('2d');
      var labels = daten.map(function(d){return new Date(d.t);});
      var werte  = daten.map(function(d){return d.v;});

      if (werte.length === 0) {
        detailDiv.innerHTML = '';
        canvas.style.display = 'none';
        var noMsg = document.createElement('div');
        noMsg.className = 'no-data-msg';
        noMsg.style.cssText = 'display:flex;align-items:center;justify-content:center;height:100%;color:var(--secondary-text);font-size:0.88rem;';
        noMsg.textContent = 'Keine Daten für diesen Zeitraum.';
        canvas.parentElement.appendChild(noMsg);
        if (sensorChart) { sensorChart.destroy(); sensorChart=null; }
        return;
      }

      var min = Math.min.apply(null, werte)-1;
      var max = Math.max.apply(null, werte)+1;
      var avg = werte.reduce(function(a,b){return a+b;},0)/werte.length;
      var aktuell = werte[werte.length-1];

      detailDiv.innerHTML =
        '<div><span class="label">Aktuell</span><span class="value">'+aktuell.toFixed(1)+' °C</span></div>'+
        '<div><span class="label">Mittel</span><span class="value">'+avg.toFixed(1)+' °C</span></div>'+
        '<div><span class="label">Min</span><span class="value">'+(min+1).toFixed(1)+' °C</span></div>'+
        '<div><span class="label">Max</span><span class="value">'+(max-1).toFixed(1)+' °C</span></div>'+
        '<div><span class="label">Messwerte</span><span class="value">'+werte.length+'</span></div>';

      if (sensorChart) { sensorChart.destroy(); }

      sensorChart = new Chart(ctx, {
        type:'line',
        data:{labels:labels,datasets:[{
          label:info.name,
          data:werte,
          borderColor:info.farbe,
          backgroundColor:info.farbe+'22',
          fill:true,
          tension:0.2,
          pointRadius:0,
          borderWidth:2,
          spanGaps:true
        }]},
        options:{
          responsive:true,
          maintainAspectRatio:false,
          interaction:{mode:'nearest',axis:'x'},
          scales:{
            x:{
              type:'time',
              time:{tooltipFormat:'dd.MM. HH:mm',displayFormats:{hour:'HH:mm',day:'dd.MM'}},
              ticks:{color:'#6b7280',maxTicksLimit:12,font:{size:10}},
              grid:{color:'#e5e7eb66'}
            },
            y:{
              ticks:{color:'#6b7280',font:{size:10}},
              grid:{color:'#e5e7eb66'},
              grace:'5%'
            }
          },
          plugins:{
            legend:{labels:{color:'#111827',boxWidth:12}}
          }
        }
      });
    }).catch(function(){
      detailDiv.innerHTML = '<div style="text-align:center;color:var(--red);padding:20px;">Fehler beim Laden.</div>';
    });
}

function openSensorModal(key) {
  if (!key) return;
  loadSensorChart(key, 24);
  document.getElementById('sensorBackdrop').classList.add('show');
}

function openPidModal() {
  document.getElementById('pidBackdrop').classList.add('show');
}

function toggleHandModus() {
  var badge = document.getElementById('modeBadge');
  var istHand = badge.classList.contains('mode-hand');
  fetch('/api/einstellungen', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({hand_modus: !istHand})
  }).then(function(r){return r.json();}).then(function(res){
    if (res.success) updateData();
  }).catch(function(){});
}

function setzeHandStellung() {
  var val = parseFloat(document.getElementById('handStellung').value);
  if (isNaN(val) || val < 0 || val > 100) return;
  fetch('/api/einstellungen', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({hand_stellwert: Math.round(val)})
  }).then(function(r){return r.json();}).then(function(res){
    if (res.success) updateData();
  }).catch(function(){});
}

function savePidSettings() {
  var data = {};
  var inputs = [
    {id:'kpInput', key:'Kp'},
    {id:'kiInput', key:'Ki'},
    {id:'kdInput', key:'Kd'},
    {id:'sollInput', key:'sollwert'},
  ];
  inputs.forEach(function(o){
    var el = document.getElementById(o.id);
    if (el) {
      var val = parseFloat(el.value);
      if (!isNaN(val)) {

        data[o.key] = val;
      }
    }
  });
  fetch('/api/einstellungen',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
    .then(function(r){return r.json();}).then(function(res){
      var status = document.getElementById('pidSaveStatus');
      if (res.success) {
        status.textContent = '\u2713 Gespeichert';
        status.style.color = '#16a34a';
      } else {
        status.textContent = '\u2717 Fehler: '+(res.error||'unbekannt');
        status.style.color = '#dc2626';
      }
      setTimeout(function(){status.textContent='';},3000);
    }).catch(function(){
      document.getElementById('pidSaveStatus').textContent = '\u2717 Verbindungsfehler';
      document.getElementById('pidSaveStatus').style.color = '#dc2626';
    });
}

document.addEventListener('DOMContentLoaded', function(){
  document.getElementById('sensor1').addEventListener('click',function(){openSensorModal('sensor_1');});
  document.getElementById('sensor2').addEventListener('click',function(){openSensorModal('sensor_2');});
  document.getElementById('sensor3').addEventListener('click',function(){openSensorModal('sensor_3');});
  document.getElementById('sensor4').addEventListener('click',function(){openSensorModal('sensor_4');});
  document.getElementById('zahnradEcke').addEventListener('click',function(e){e.preventDefault();openPidModal();});

  document.getElementById('pidClose').addEventListener('click',function(){document.getElementById('pidBackdrop').classList.remove('show');});
  document.getElementById('pidBackdrop').addEventListener('click',function(e){if(e.target===this)this.classList.remove('show');});

  document.getElementById('sensorClose').addEventListener('click',function(){document.getElementById('sensorBackdrop').classList.remove('show');});
  document.getElementById('sensorBackdrop').addEventListener('click',function(e){if(e.target===this)this.classList.remove('show');});

  document.getElementById('btnSavePid').addEventListener('click',savePidSettings);
  document.getElementById('modeBadge').addEventListener('click', toggleHandModus);
  document.getElementById('btnHandSet').addEventListener('click', setzeHandStellung);
  document.getElementById('handStellung').addEventListener('keydown', function(e){
    if (e.key === 'Enter') setzeHandStellung();
  });

  document.querySelectorAll('[data-sensor-std]').forEach(function(btn){
    btn.addEventListener('click',function(){
      document.querySelectorAll('[data-sensor-std]').forEach(function(b){b.classList.remove('aktiv');});
      this.classList.add('aktiv');
      if (sensorAktKey) loadSensorChart(sensorAktKey, parseInt(this.dataset.sensorStd));
    });
  });

  updateData();
  setInterval(updateData, 3000);
  setTimeout(updateLinePositions, 200);
  window.addEventListener('resize', updateLinePositions);
});

})();
