(function(){
'use strict';

var hauptChart = null;
var auswahlTimeout = null;

var KANAL_MAP = {
  "ist_temp": "Ist-Temperatur",
  "sollwert": "Sollwert",
  "pid_out": "PID-Ausgabe",
  "ventil": "Ventil-Position",
  "temp_1": "Sensor 1",
  "temp_2": "Sensor 2",
  "temp_3": "Sensor 3",
  "temp_4": "Sensor 4",
};

function fmtDT(d) {
  var y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), day=String(d.getDate()).padStart(2,'0');
  var h=String(d.getHours()).padStart(2,'0'), min=String(d.getMinutes()).padStart(2,'0');
  return y+'-'+m+'-'+day+' '+h+':'+min;
}

function getZeitraum() {
  var akt = document.querySelector('.zeitraum-btn.aktiv');
  var std = akt ? parseInt(akt.dataset.std) : 24;
  var bis = new Date();
  var von = new Date(bis.getTime() - std*3600000);
  return {von:von, bis:bis};
}

function getAktiveKanaele() {
  var cbs = document.querySelectorAll('.kanal-cb:checked');
  var result = [];
  cbs.forEach(function(cb){result.push(cb.value);});
  return result;
}

function kanalPanelBauen() {
  var gruppen = [
    {titel:'Temperaturen', kanaele:['ist_temp','temp_1','temp_2','temp_3','temp_4']},
    {titel:'Regelung', kanaele:['sollwert','pid_out','ventil']},
  ];
  var container = document.getElementById('kanalGruppen');
  var html = '';
  gruppen.forEach(function(g){
    html += '<div class="kanal-gruppe"><div class="kanal-gruppe-titel">'+g.titel+'</div><div class="kanal-checkboxen">';
    g.kanaele.forEach(function(k){
      var name = KANAL_MAP[k] || k;
      var checked = (k==='ist_temp'||k==='sollwert'||k==='pid_out') ? ' checked' : '';
      html += '<label class="kanal-label"><input type="checkbox" class="kanal-cb" value="'+k+'"'+checked+'> '+name+'</label>';
    });
    html += '</div></div>';
  });
  container.innerHTML = html;
  container.querySelectorAll('.kanal-cb').forEach(function(cb){
    cb.addEventListener('change', function(){
      if (auswahlTimeout) clearTimeout(auswahlTimeout);
      auswahlTimeout = setTimeout(laden, 500);
    });
  });
}

var PALETTE = ['#ef4444','#3b82f6','#16a34a','#d97706','#e3b341','#8b5cf6','#f0883e','#7ee787','#79b8ff','#ff7b72'];

function laden() {
  var kanaele = getAktiveKanaele();
  var info = document.getElementById('chartInfo');
  if (kanaele.length === 0) {
    info.textContent = 'Bitte mindestens einen Kanal auswählen.';
    if (hauptChart) { hauptChart.destroy(); hauptChart = null; }
    return;
  }
  var zp = getZeitraum();
  document.getElementById('zeitVon').value = fmtDT(zp.von).replace(' ','T');
  document.getElementById('zeitBis').value = fmtDT(zp.bis).replace(' ','T');
  info.textContent = 'Lade Daten ('+kanaele.length+' Kanäle) …';

  var body = JSON.stringify({kanaele:kanaele, von:fmtDT(zp.von), bis:fmtDT(zp.bis)});
  fetch('/api/historie/multi',{method:'POST',headers:{'Content-Type':'application/json'},body:body})
    .then(function(r){return r.json();}).then(function(res){
      var alleDaten = res.daten || {};
      var anzahl = 0;
      Object.values(alleDaten).forEach(function(arr){anzahl += arr.length;});
      info.textContent = kanaele.length+' Kanäle | '+anzahl+' Datenpunkte';

      if (hauptChart) { hauptChart.destroy(); hauptChart = null; }
      var ctx = document.getElementById('hauptChartCanvas').getContext('2d');
      var allTimes = new Set();
      Object.values(alleDaten).forEach(function(arr){arr.forEach(function(d){allTimes.add(d.t);});});
      var sortedTimes = Array.from(allTimes).sort();

      var datasets = [];
      var farbIdx = 0;
      Object.entries(alleDaten).forEach(function(entry){
        var kid = entry[0], arr = entry[1];
        var dataMap = {};
        arr.forEach(function(d){dataMap[d.t]=d.v;});
        var data = sortedTimes.map(function(ts){
          return {x:new Date(ts), y: dataMap[ts] !== undefined ? dataMap[ts] : null};
        });
        datasets.push({
          label: KANAL_MAP[kid] || kid,
          data: data,
          borderColor: PALETTE[farbIdx % PALETTE.length],
          backgroundColor: PALETTE[farbIdx % PALETTE.length]+'22',
          fill: false,
          tension: 0.2,
          pointRadius: 0,
          borderWidth: 2,
          spanGaps: true,
        });
        farbIdx++;
      });

      hauptChart = new Chart(ctx, {
        type:'line',
        data:{datasets:datasets},
        options:{
          responsive:true,
          maintainAspectRatio:false,
          interaction:{mode:'nearest',axis:'x'},
          scales:{
            x:{
              type:'time',
              time:{tooltipFormat:'dd.MM. HH:mm',displayFormats:{hour:'HH:mm',day:'dd.MM',week:'dd.MM'}},
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
            legend:{
              labels:{color:'#111827',boxWidth:14,font:{size:11}},
              onClick:function(e,legendItem,chart){
                var idx = legendItem.datasetIndex;
                var meta = chart.getDatasetMeta(idx);
                meta.hidden = meta.hidden === null ? !chart.data.datasets[idx].hidden : null;
                chart.update();
              }
            },
            tooltip:{mode:'index',intersect:false,titleFont:{size:11},bodyFont:{size:10},padding:8}
          }
        }
      });
    }).catch(function(err){
      info.textContent = 'Fehler: '+err.message;
    });
}

document.addEventListener('DOMContentLoaded', function(){
  kanalPanelBauen();

  document.querySelectorAll('.zeitraum-btn').forEach(function(btn){
    btn.addEventListener('click', function(){
      document.querySelectorAll('.zeitraum-btn').forEach(function(b){b.classList.remove('aktiv');});
      this.classList.add('aktiv');
      laden();
    });
  });

  document.getElementById('btnLaden').addEventListener('click', laden);

  document.getElementById('btnKanalToggle').addEventListener('click', function(){
    var panel = document.getElementById('kanalPanel');
    panel.classList.toggle('collapsed');
    this.textContent = panel.classList.contains('collapsed') ? '\u25B8 Kan\u00E4le einblenden' : '\u25BE Kan\u00E4le ausblenden';
  });

  laden();

  fetch('/api/alarme').then(function(r){return r.json();}).then(function(res){
    var badge = document.getElementById('alarmBadge');
    if (badge) {
      var count = res.anzahl_aktiv || 0;
      badge.textContent = count;
      badge.style.display = count > 0 ? 'flex' : 'none';
    }
  }).catch(function(){});
});

})();
