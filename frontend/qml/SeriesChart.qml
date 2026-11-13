import QtQuick
import QtQuick.Layouts

// One signal over time, with the person's own normal drawn behind it as a band.
ColumnLayout {
    id: root
    property var series
    property int chartHeight: 220
    property int picked: -1
    spacing: 2

    readonly property int n: series ? series.days.length : 0
    readonly property int shown: picked >= 0 ? picked : nearest(n - 1)
    readonly property var value: shown >= 0 && series ? series.values[shown] : null
    readonly property var low: shown >= 0 && series ? series.low[shown] : null
    readonly property var high: shown >= 0 && series ? series.high[shown] : null

    function present(v) { return v !== null && v !== undefined }
    function nearest(i) {
        if (!series) return -1
        for (var step = 0; step < n; step++) {
            if (i - step >= 0 && present(series.values[i - step])) return i - step
            if (i + step < n && present(series.values[i + step])) return i + step
        }
        return -1
    }
    function pick(px) {
        var ratio = (px - m.left) / (canvas.width - m.left - m.right)
        picked = nearest(Math.max(0, Math.min(n - 1, Math.round(ratio * (n - 1)))))
    }
    readonly property var m: ({ left: 62, right: 14, top: 12, bottom: 30 })
    readonly property int tickDecimals: {
        if (!series) return 0
        var all = series.values.concat(series.low, series.high).filter(present)
        return Math.max.apply(null, all) - Math.min.apply(null, all) < 3 ? Math.max(series.decimals, 1) : series.decimals
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.preferredHeight: 30
        spacing: 16
        Text { visible: root.present(root.value); text: "Day " + (root.series ? root.series.days[root.shown] : ""); font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 17; color: Theme.ink }
        Text { visible: root.present(root.value); text: root.present(root.value) ? root.value.toFixed(root.series.decimals) + " " + root.series.unit : ""; font.family: Theme.body; font.pixelSize: 17; color: Theme.ink }
        Text {
            text: !root.present(root.value) ? "No reading on this day" : root.present(root.low) && root.present(root.high) ? "Usual range " + root.low.toFixed(root.tickDecimals) + " to " + root.high.toFixed(root.tickDecimals) : "Needs more readings"
            font.family: Theme.body; font.pixelSize: 17; color: Theme.ink2
        }
        StatusPill { visible: root.shown >= 0 && !!root.series && root.series.flagged[root.shown]; status: "yellow"; label: "Drifting"; compact: true }
        Item { Layout.fillWidth: true }
    }

    Canvas {
        id: canvas
        Layout.fillWidth: true
        Layout.preferredHeight: root.chartHeight
        activeFocusOnTab: true
        Accessible.role: Accessible.Graphic
        Accessible.name: root.series ? root.series.name + " chart. Latest " + root.series.current + " " + root.series.unit + ". Use the left and right arrow keys to read each day." : ""

        Keys.onLeftPressed: root.picked = Math.max(0, (root.picked >= 0 ? root.picked : root.n - 1) - 1)
        Keys.onRightPressed: root.picked = Math.min(root.n - 1, (root.picked >= 0 ? root.picked : root.n - 1) + 1)

        Connections { target: root; function onSeriesChanged() { canvas.requestPaint() } function onShownChanged() { canvas.requestPaint() } }
        Connections { target: Theme; function onModeChanged() { canvas.requestPaint() } }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onActiveFocusChanged: requestPaint()

        MouseArea {
            anchors.fill: parent
            onPressed: function (e) { canvas.forceActiveFocus(); root.pick(e.x) }
            onPositionChanged: function (e) { if (pressed) root.pick(e.x) }
        }

        onPaint: {
            var c = getContext("2d")
            c.reset()
            var s = root.series
            if (!s || !root.n) return
            var m = root.m, n = root.n, present = root.present
            var plotW = width - m.left - m.right, plotH = height - m.top - m.bottom
            var all = s.values.concat(s.low, s.high).filter(present)
            var min = Math.min.apply(null, all), max = Math.max.apply(null, all)
            var pad = (max - min || 1) * 0.08
            var lo = min - pad, hi = max + pad
            function x(i) { return m.left + (n > 1 ? i / (n - 1) * plotW : plotW / 2) }
            function y(v) { return m.top + (1 - (v - lo) / (hi - lo)) * plotH }

            c.font = "16px '" + Theme.body + "'"
            c.textBaseline = "middle"
            ;[lo + (hi - lo) * 0.1, (lo + hi) / 2, hi - (hi - lo) * 0.1].forEach(function (t) {
                c.strokeStyle = Theme.rule; c.globalAlpha = 0.9; c.lineWidth = 1
                c.beginPath(); c.moveTo(m.left, y(t)); c.lineTo(width - m.right, y(t)); c.stroke()
                c.globalAlpha = 1; c.fillStyle = Theme.ink2; c.textAlign = "right"
                c.fillText(t.toFixed(root.tickDecimals), m.left - 8, y(t))
            })

            var band = []
            for (var i = 0; i < n; i++) if (present(s.low[i]) && present(s.high[i])) band.push(i)
            if (band.length > 1) {
                c.fillStyle = Theme.band; c.globalAlpha = 0.16
                c.beginPath()
                band.forEach(function (b, k) { k ? c.lineTo(x(b), y(s.high[b])) : c.moveTo(x(b), y(s.high[b])) })
                band.slice().reverse().forEach(function (b) { c.lineTo(x(b), y(s.low[b])) })
                c.closePath(); c.fill(); c.globalAlpha = 1
                c.strokeStyle = Theme.band; c.globalAlpha = 0.6; c.lineWidth = 1.5; c.setLineDash([2, 5])
                c.beginPath()
                band.forEach(function (b, k) { k ? c.lineTo(x(b), y(s.median[b])) : c.moveTo(x(b), y(s.median[b])) })
                c.stroke(); c.setLineDash([]); c.globalAlpha = 1
                if (band[0] > 0) { c.fillStyle = Theme.ink2; c.textAlign = "right"; c.fillText("Baseline period", x(band[0]) - 6, m.top + 12) }
            }

            c.strokeStyle = Theme.ink; c.lineWidth = 2; c.lineJoin = "round"
            c.beginPath()
            var started = false
            for (i = 0; i < n; i++) {
                if (!present(s.values[i])) continue
                started ? c.lineTo(x(i), y(s.values[i])) : c.moveTo(x(i), y(s.values[i]))
                started = true
            }
            c.stroke()

            for (i = 0; i < n; i++) {
                if (!present(s.values[i])) continue
                if (s.cadence > 1) { c.fillStyle = Theme.ink; c.beginPath(); c.arc(x(i), y(s.values[i]), 3.5, 0, Math.PI * 2); c.fill() }
                if (s.flagged[i]) {
                    c.fillStyle = Theme.flag; c.strokeStyle = Theme.panel; c.lineWidth = 2
                    c.beginPath(); c.arc(x(i), y(s.values[i]), 5, 0, Math.PI * 2); c.fill(); c.stroke()
                }
            }

            if (root.shown >= 0) {
                c.strokeStyle = activeFocus ? Theme.action : Theme.ink2; c.lineWidth = activeFocus ? 2 : 1
                c.beginPath(); c.moveTo(x(root.shown), m.top); c.lineTo(x(root.shown), m.top + plotH); c.stroke()
            }
            c.fillStyle = Theme.ink2; c.textBaseline = "alphabetic"
            c.textAlign = "left"; c.fillText("Day " + s.days[0], m.left, height - 8)
            c.textAlign = "right"; c.fillText("Day " + s.days[n - 1], width - m.right, height - 8)
        }
    }
}
