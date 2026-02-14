// NYS District Dashboard - Main Application
// Lightweight chart renderer using vanilla JavaScript and SVG

class ChartRenderer {
    constructor() {
        this.margin = { top: 40, right: 80, bottom: 60, left: 60 };
        this.width = 800;
        this.height = 400;
        this.hiddenSeries = new Set();

        // Create tooltip div for data point hover
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'chart-tooltip';
        this.tooltip.style.display = 'none';
        document.body.appendChild(this.tooltip);
    }

    /**
     * Render a line chart
     */
    renderLineChart(svg, spec) {
        const { data, xAxis, yAxis, series, title } = spec;
        
        if (!data || data.length === 0) {
            this.renderNoData(svg, title);
            return;
        }

        // Calculate dimensions
        const chartWidth = this.width - this.margin.left - this.margin.right;
        const chartHeight = this.height - this.margin.top - this.margin.bottom;

        // Get x and y ranges
        const xValues = data.map(d => d[xAxis.field]);
        const isNumericX = xValues.every(v => typeof v === 'number' && !isNaN(v));
        const uniqueXValues = [...new Set(xValues)].sort((a, b) => isNumericX ? a - b : String(a).localeCompare(String(b)));

        let xMin, xMax, xRange, xScale;
        if (isNumericX) {
            xMin = Math.min(...xValues);
            xMax = Math.max(...xValues);
            xRange = xMax - xMin;
            xScale = (value) => {
                return this.margin.left + (value - xMin) / (xRange || 1) * chartWidth;
            };
        } else {
            xMin = uniqueXValues[0];
            xMax = uniqueXValues[uniqueXValues.length - 1];
            xRange = uniqueXValues.length - 1;
            xScale = (value) => {
                const idx = uniqueXValues.indexOf(String(value));
                return this.margin.left + (idx >= 0 ? idx : 0) / (xRange || 1) * chartWidth;
            };
        }
        
        const yMin = yAxis.min !== undefined ? yAxis.min : 0;
        const yMax = yAxis.max !== undefined ? yAxis.max : 100;
        const yRange = yMax - yMin;

        const yScale = (value) => {
            return this.height - this.margin.bottom - (value - yMin) / (yRange || 1) * chartHeight;
        };

        // Clear SVG
        svg.innerHTML = '';
        svg.setAttribute('viewBox', `0 0 ${this.width} ${this.height}`);

        // Draw grid lines
        for (let i = 0; i <= 5; i++) {
            const y = this.margin.top + (chartHeight / 5) * i;
            const gridLine = this.createSVGElement('line', {
                x1: this.margin.left,
                y1: y,
                x2: this.width - this.margin.right,
                y2: y,
                class: 'grid-line'
            });
            svg.appendChild(gridLine);
        }

        // Draw axes
        if (isNumericX) {
            this.drawAxes(svg, chartWidth, chartHeight, xMin, xMax, yMin, yMax, xAxis, yAxis);
        } else {
            this.drawCategoryAxes(svg, chartWidth, chartHeight, uniqueXValues, yMin, yMax, xAxis, yAxis);
        }

        // Track elements per series for interactive legend
        const seriesElements = [];

        // Draw series
        series.forEach((s, idx) => {
            const seriesData = data.filter(d => {
                if (!s.filter) return true;
                return Object.entries(s.filter).every(([key, val]) => d[key] === val);
            });

            if (seriesData.length === 0) {
                seriesElements.push({ paths: [], circles: [] });
                return;
            }

            // Sort by x value
            if (isNumericX) {
                seriesData.sort((a, b) => a[xAxis.field] - b[xAxis.field]);
            } else {
                seriesData.sort((a, b) => uniqueXValues.indexOf(String(a[xAxis.field])) - uniqueXValues.indexOf(String(b[xAxis.field])));
            }

            // Draw line
            const points = seriesData.map(d => ({
                x: xScale(d[xAxis.field]),
                y: yScale(d[s.field]),
                xVal: d[xAxis.field],
                yVal: d[s.field],
                source_url: d.source_url || null
            }));

            const pathData = points.map((p, i) => 
                `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`
            ).join(' ');

            const path = this.createSVGElement('path', {
                d: pathData,
                class: 'data-line',
                stroke: s.color || '#1f77b4',
                'stroke-width': s.dashStyle === 'dashed' ? 2.5 : 2,
                'stroke-dasharray': s.dashStyle === 'dashed' ? '6,3' : 'none',
                fill: 'none',
                'data-series-index': idx
            });
            svg.appendChild(path);

            // Draw data points with tooltips
            const circles = [];
            points.forEach(p => {
                const circle = this.createSVGElement('circle', {
                    cx: p.x,
                    cy: p.y,
                    r: 4,
                    fill: s.color || '#1f77b4',
                    class: 'data-point',
                    'data-series-index': idx
                });

                circle.addEventListener('mouseenter', (e) => {
                    this.showTooltip(e, `${s.name}: ${p.yVal}`, `${xAxis.label}: ${p.xVal}`, p.source_url);
                });
                circle.addEventListener('mouseleave', () => {
                    this.hideTooltip();
                });

                svg.appendChild(circle);
                circles.push(circle);
            });

            seriesElements.push({ paths: [path], circles: circles });
        });

        // Draw interactive legend
        this.drawInteractiveLegend(svg, series, this.width - this.margin.right - 10, seriesElements);

        // Draw annotations if present
        if (spec.annotations) {
            this.renderAnnotations(svg, spec.annotations, xAxis, xScale, chartHeight, isNumericX, uniqueXValues);
        }
    }

    /**
     * Render a bar chart
     */
    renderBarChart(svg, spec) {
        const { data, xAxis, yAxis, series, title } = spec;
        
        if (!data || data.length === 0) {
            this.renderNoData(svg, title);
            return;
        }

        // Calculate dimensions
        const chartWidth = this.width - this.margin.left - this.margin.right;
        const chartHeight = this.height - this.margin.top - this.margin.bottom;

        // Get y range
        const yValues = data.map(d => d[series[0].field]);
        const yMin = yAxis.min !== undefined ? yAxis.min : Math.min(0, ...yValues);
        const yMax = yAxis.max !== undefined ? yAxis.max : Math.max(...yValues);
        const yRange = yMax - yMin;

        // Create scale
        const yScale = (value) => {
            return this.height - this.margin.bottom - (value - yMin) / (yRange || 1) * chartHeight;
        };

        // Clear SVG
        svg.innerHTML = '';
        svg.setAttribute('viewBox', `0 0 ${this.width} ${this.height}`);

        // Draw grid lines
        for (let i = 0; i <= 5; i++) {
            const y = this.margin.top + (chartHeight / 5) * i;
            const gridLine = this.createSVGElement('line', {
                x1: this.margin.left,
                y1: y,
                x2: this.width - this.margin.right,
                y2: y,
                class: 'grid-line'
            });
            svg.appendChild(gridLine);
        }

        // Draw axes
        const xLabels = data.map(d => d[xAxis.field]);
        this.drawBarAxes(svg, chartWidth, chartHeight, xLabels, yMin, yMax, xAxis, yAxis);

        // Draw bars
        const barWidth = chartWidth / data.length * 0.7;
        const barSpacing = chartWidth / data.length;

        data.forEach((d, i) => {
            const value = d[series[0].field];
            const barHeight = Math.abs(yScale(value) - yScale(0));
            const barX = this.margin.left + i * barSpacing + (barSpacing - barWidth) / 2;
            const barY = Math.min(yScale(value), yScale(0));

            const rect = this.createSVGElement('rect', {
                x: barX,
                y: barY,
                width: barWidth,
                height: barHeight,
                fill: series[0].color || '#2ca02c',
                class: 'data-bar'
            });
            svg.appendChild(rect);

            // Add value label on top of bar
            const label = this.createSVGElement('text', {
                x: barX + barWidth / 2,
                y: barY - 5,
                'text-anchor': 'middle',
                class: 'axis-text'
            });
            label.textContent = value.toFixed(1) + '%';
            svg.appendChild(label);
        });

        // Draw annotations if present
        if (spec.annotations) {
            const xLabels = data.map(d => d[xAxis.field]);
            const barXScale = (value) => {
                const i = xLabels.indexOf(value);
                if (i < 0) return this.margin.left;
                return this.margin.left + i * barSpacing + barSpacing / 2;
            };
            this.renderAnnotations(svg, spec.annotations, xAxis, barXScale, chartHeight, false, xLabels);
        }
    }

    /**
     * Draw axes for line chart
     */
    drawAxes(svg, chartWidth, chartHeight, xMin, xMax, yMin, yMax, xAxis, yAxis) {
        // X axis
        const xAxisLine = this.createSVGElement('line', {
            x1: this.margin.left,
            y1: this.height - this.margin.bottom,
            x2: this.width - this.margin.right,
            y2: this.height - this.margin.bottom,
            class: 'axis-line'
        });
        svg.appendChild(xAxisLine);

        // Y axis
        const yAxisLine = this.createSVGElement('line', {
            x1: this.margin.left,
            y1: this.margin.top,
            x2: this.margin.left,
            y2: this.height - this.margin.bottom,
            class: 'axis-line'
        });
        svg.appendChild(yAxisLine);

        // X axis label
        const xLabel = this.createSVGElement('text', {
            x: this.margin.left + chartWidth / 2,
            y: this.height - 10,
            'text-anchor': 'middle',
            class: 'axis-label'
        });
        xLabel.textContent = xAxis.label;
        svg.appendChild(xLabel);

        // Y axis label
        const yLabel = this.createSVGElement('text', {
            x: 15,
            y: this.margin.top + chartHeight / 2,
            'text-anchor': 'middle',
            class: 'axis-label',
            transform: `rotate(-90, 15, ${this.margin.top + chartHeight / 2})`
        });
        yLabel.textContent = yAxis.label;
        svg.appendChild(yLabel);

        // X tick labels
        const xRange = xMax - xMin || 1;
        const xStep = xRange > 5 ? Math.ceil(xRange / 5) : 1;
        for (let x = xMin; x <= xMax; x += xStep) {
            const xPos = this.margin.left + (x - xMin) / xRange * chartWidth;
            const tick = this.createSVGElement('text', {
                x: xPos,
                y: this.height - this.margin.bottom + 20,
                'text-anchor': 'middle',
                class: 'axis-text'
            });
            tick.textContent = x;
            svg.appendChild(tick);
        }

        // Y tick labels
        for (let i = 0; i <= 5; i++) {
            const value = yMin + (yMax - yMin) * i / 5;
            const yPos = this.height - this.margin.bottom - chartHeight * i / 5;
            const tick = this.createSVGElement('text', {
                x: this.margin.left - 10,
                y: yPos + 5,
                'text-anchor': 'end',
                class: 'axis-text'
            });
            tick.textContent = value.toFixed(0);
            svg.appendChild(tick);
        }
    }

    /**
     * Draw axes for line chart with category (string) x-axis
     */
    drawCategoryAxes(svg, chartWidth, chartHeight, xCategories, yMin, yMax, xAxis, yAxis) {
        // X axis
        const xAxisLine = this.createSVGElement('line', {
            x1: this.margin.left,
            y1: this.height - this.margin.bottom,
            x2: this.width - this.margin.right,
            y2: this.height - this.margin.bottom,
            class: 'axis-line'
        });
        svg.appendChild(xAxisLine);

        // Y axis
        const yAxisLine = this.createSVGElement('line', {
            x1: this.margin.left,
            y1: this.margin.top,
            x2: this.margin.left,
            y2: this.height - this.margin.bottom,
            class: 'axis-line'
        });
        svg.appendChild(yAxisLine);

        // X axis label
        const xLabel = this.createSVGElement('text', {
            x: this.margin.left + chartWidth / 2,
            y: this.height - 10,
            'text-anchor': 'middle',
            class: 'axis-label'
        });
        xLabel.textContent = xAxis.label;
        svg.appendChild(xLabel);

        // Y axis label
        const yLabel = this.createSVGElement('text', {
            x: 15,
            y: this.margin.top + chartHeight / 2,
            'text-anchor': 'middle',
            class: 'axis-label',
            transform: `rotate(-90, 15, ${this.margin.top + chartHeight / 2})`
        });
        yLabel.textContent = yAxis.label;
        svg.appendChild(yLabel);

        // X tick labels (categories)
        const catCount = xCategories.length;
        xCategories.forEach((cat, i) => {
            const xPos = this.margin.left + (i / (catCount - 1 || 1)) * chartWidth;
            const tick = this.createSVGElement('text', {
                x: xPos,
                y: this.height - this.margin.bottom + 20,
                'text-anchor': 'middle',
                class: 'axis-text'
            });
            tick.textContent = cat;
            svg.appendChild(tick);
        });

        // Y tick labels
        for (let i = 0; i <= 5; i++) {
            const value = yMin + (yMax - yMin) * i / 5;
            const yPos = this.height - this.margin.bottom - chartHeight * i / 5;
            const tick = this.createSVGElement('text', {
                x: this.margin.left - 10,
                y: yPos + 5,
                'text-anchor': 'end',
                class: 'axis-text'
            });
            tick.textContent = value.toFixed(1);
            svg.appendChild(tick);
        }
    }

    /**
     * Draw axes for bar chart
     */
    drawBarAxes(svg, chartWidth, chartHeight, xLabels, yMin, yMax, xAxis, yAxis) {
        // X axis
        const xAxisLine = this.createSVGElement('line', {
            x1: this.margin.left,
            y1: this.height - this.margin.bottom,
            x2: this.width - this.margin.right,
            y2: this.height - this.margin.bottom,
            class: 'axis-line'
        });
        svg.appendChild(xAxisLine);

        // Y axis
        const yAxisLine = this.createSVGElement('line', {
            x1: this.margin.left,
            y1: this.margin.top,
            x2: this.margin.left,
            y2: this.height - this.margin.bottom,
            class: 'axis-line'
        });
        svg.appendChild(yAxisLine);

        // X axis label
        const xLabel = this.createSVGElement('text', {
            x: this.margin.left + chartWidth / 2,
            y: this.height - 10,
            'text-anchor': 'middle',
            class: 'axis-label'
        });
        xLabel.textContent = xAxis.label;
        svg.appendChild(xLabel);

        // Y axis label
        const yLabel = this.createSVGElement('text', {
            x: 15,
            y: this.margin.top + chartHeight / 2,
            'text-anchor': 'middle',
            class: 'axis-label',
            transform: `rotate(-90, 15, ${this.margin.top + chartHeight / 2})`
        });
        yLabel.textContent = yAxis.label;
        svg.appendChild(yLabel);

        // X tick labels (category labels)
        const barSpacing = chartWidth / xLabels.length;
        xLabels.forEach((label, i) => {
            const xPos = this.margin.left + i * barSpacing + barSpacing / 2;
            const tick = this.createSVGElement('text', {
                x: xPos,
                y: this.height - this.margin.bottom + 20,
                'text-anchor': 'middle',
                class: 'axis-text'
            });
            tick.textContent = label;
            svg.appendChild(tick);
        });

        // Y tick labels
        for (let i = 0; i <= 5; i++) {
            const value = yMin + (yMax - yMin) * i / 5;
            const yPos = this.height - this.margin.bottom - chartHeight * i / 5;
            const tick = this.createSVGElement('text', {
                x: this.margin.left - 10,
                y: yPos + 5,
                'text-anchor': 'end',
                class: 'axis-text'
            });
            tick.textContent = value.toFixed(1);
            svg.appendChild(tick);
        }
    }

    /**
     * Draw legend
     */
    drawLegend(svg, series, x) {
        let y = this.margin.top;
        
        series.forEach((s, i) => {
            const legendY = y + i * 25;
            
            // Color box
            const rect = this.createSVGElement('rect', {
                x: x - 60,
                y: legendY - 10,
                width: 15,
                height: 15,
                fill: s.color || '#1f77b4',
                class: 'legend-rect'
            });
            svg.appendChild(rect);
            
            // Label
            const text = this.createSVGElement('text', {
                x: x - 40,
                y: legendY,
                class: 'legend-text'
            });
            text.textContent = s.name;
            svg.appendChild(text);
        });
    }

    /**
     * Draw interactive legend with click-to-toggle and hover-to-highlight
     */
    drawInteractiveLegend(svg, series, x, seriesElements) {
        let y = this.margin.top;

        series.forEach((s, i) => {
            const legendY = y + i * 25;

            const group = this.createSVGElement('g', {
                class: 'legend-item',
                'data-series-index': i,
                style: 'cursor: pointer;'
            });

            const rect = this.createSVGElement('rect', {
                x: x - 60,
                y: legendY - 10,
                width: 15,
                height: 15,
                fill: s.color || '#1f77b4',
                class: 'legend-rect'
            });
            group.appendChild(rect);

            const text = this.createSVGElement('text', {
                x: x - 40,
                y: legendY,
                class: 'legend-text'
            });
            text.textContent = s.name;
            group.appendChild(text);

            // Click to toggle series visibility
            group.addEventListener('click', () => {
                const elems = seriesElements[i];
                if (!elems) return;
                const isHidden = this.hiddenSeries.has(i);
                if (isHidden) {
                    this.hiddenSeries.delete(i);
                    elems.paths.forEach(p => p.style.display = '');
                    elems.circles.forEach(c => c.style.display = '');
                    rect.setAttribute('opacity', '1');
                    text.setAttribute('opacity', '1');
                } else {
                    this.hiddenSeries.add(i);
                    elems.paths.forEach(p => p.style.display = 'none');
                    elems.circles.forEach(c => c.style.display = 'none');
                    rect.setAttribute('opacity', '0.3');
                    text.setAttribute('opacity', '0.3');
                }
            });

            // Hover to highlight corresponding series
            group.addEventListener('mouseenter', () => {
                seriesElements.forEach((elems, j) => {
                    if (!elems) return;
                    const dim = j !== i;
                    elems.paths.forEach(p => { p.style.opacity = dim ? '0.2' : '1'; });
                    elems.circles.forEach(c => { c.style.opacity = dim ? '0.2' : '1'; });
                });
            });
            group.addEventListener('mouseleave', () => {
                seriesElements.forEach((elems, j) => {
                    if (!elems) return;
                    const hidden = this.hiddenSeries.has(j);
                    elems.paths.forEach(p => { p.style.opacity = hidden ? '0' : '1'; });
                    elems.circles.forEach(c => { c.style.opacity = hidden ? '0' : '1'; });
                });
            });

            svg.appendChild(group);
        });
    }

    /**
     * Render annotation markers on the chart
     */
    renderAnnotations(svg, annotations, xAxis, xScale, chartHeight, isNumericX, uniqueXValues) {
        if (!annotations || annotations.length === 0) return;

        annotations.forEach(ann => {
            const xPos = xScale(ann.x);
            if (xPos === undefined || isNaN(xPos)) return;

            // Dashed vertical line
            const line = this.createSVGElement('line', {
                x1: xPos,
                y1: this.margin.top,
                x2: xPos,
                y2: this.height - this.margin.bottom,
                stroke: '#FF4D4D',
                'stroke-opacity': '0.4',
                'stroke-width': '1.5',
                'stroke-dasharray': '5,4',
                class: 'annotation-line'
            });
            svg.appendChild(line);

            // Marker circle wrapped in accessible <a> element
            const anchor = this.createSVGElement('a', {
                tabindex: '0',
                role: 'button',
                'aria-label': ann.label || 'Annotation'
            });

            const marker = this.createSVGElement('circle', {
                cx: xPos,
                cy: this.margin.top - 6,
                r: 5,
                fill: '#FF4D4D',
                class: 'annotation-marker',
                style: 'cursor: pointer;'
            });
            anchor.appendChild(marker);

            // Tooltip group (hidden by default)
            const tipWidth = 200;
            const tipX = Math.min(xPos - tipWidth / 2, this.width - tipWidth - 10);
            const tipGroup = this.createSVGElement('g', {
                class: 'annotation-tooltip',
                style: 'display: none;'
            });

            const tipBg = this.createSVGElement('rect', {
                x: tipX,
                y: this.margin.top - 70,
                width: tipWidth,
                height: 58,
                rx: 4,
                fill: '#1a1a2e',
                stroke: '#FF4D4D',
                'stroke-width': '0.5',
                opacity: '0.95'
            });
            tipGroup.appendChild(tipBg);

            let textY = this.margin.top - 55;
            if (ann.label) {
                const labelText = this.createSVGElement('text', {
                    x: tipX + 8,
                    y: textY,
                    fill: '#ffffff',
                    'font-size': '11px',
                    'font-weight': 'bold'
                });
                labelText.textContent = ann.label;
                tipGroup.appendChild(labelText);
                textY += 14;
            }
            if (ann.detail) {
                const detailText = this.createSVGElement('text', {
                    x: tipX + 8,
                    y: textY,
                    fill: '#cccccc',
                    'font-size': '10px'
                });
                detailText.textContent = ann.detail;
                tipGroup.appendChild(detailText);
                textY += 13;
            }
            if (ann.category) {
                const catText = this.createSVGElement('text', {
                    x: tipX + 8,
                    y: textY,
                    fill: '#aaaaaa',
                    'font-size': '9px'
                });
                catText.textContent = ann.category;
                tipGroup.appendChild(catText);
                textY += 13;
            }
            if (ann.url) {
                const linkText = this.createSVGElement('text', {
                    x: tipX + 8,
                    y: textY,
                    fill: '#5dade2',
                    'font-size': '10px',
                    style: 'cursor: pointer;'
                });
                linkText.textContent = 'Open source \u2192';
                tipGroup.appendChild(linkText);
            }

            svg.appendChild(tipGroup);

            // Show/hide tooltip on hover and focus
            const showTip = () => { tipGroup.style.display = ''; };
            const hideTip = () => { tipGroup.style.display = 'none'; };
            anchor.addEventListener('mouseenter', showTip);
            anchor.addEventListener('mouseleave', hideTip);
            anchor.addEventListener('focus', showTip);
            anchor.addEventListener('blur', hideTip);

            // Click opens URL in new tab if present
            if (ann.url) {
                anchor.addEventListener('click', () => {
                    window.open(ann.url, '_blank', 'noopener');
                });
                anchor.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        window.open(ann.url, '_blank', 'noopener');
                    }
                });
            }

            svg.appendChild(anchor);
        });
    }

    /**
     * Show data point tooltip
     */
    showTooltip(event, valueLine, xLine, sourceUrl) {
        this.tooltip.innerHTML = '';
        const val = document.createElement('div');
        val.style.fontWeight = 'bold';
        val.textContent = valueLine;
        this.tooltip.appendChild(val);

        const xInfo = document.createElement('div');
        xInfo.textContent = xLine;
        this.tooltip.appendChild(xInfo);

        if (sourceUrl) {
            const link = document.createElement('a');
            link.href = sourceUrl;
            link.target = '_blank';
            link.rel = 'noopener';
            link.textContent = 'Source \u2192';
            link.style.color = '#5dade2';
            link.style.fontSize = '11px';
            this.tooltip.appendChild(link);
        }

        this.tooltip.style.display = 'block';
        this.tooltip.style.left = (event.pageX + 12) + 'px';
        this.tooltip.style.top = (event.pageY - 30) + 'px';
    }

    /**
     * Hide data point tooltip
     */
    hideTooltip() {
        this.tooltip.style.display = 'none';
    }

    /**
     * Render "no data" message
     */
    renderNoData(svg, title) {
        svg.innerHTML = '';
        svg.setAttribute('viewBox', `0 0 ${this.width} ${this.height}`);
        
        const text = this.createSVGElement('text', {
            x: this.width / 2,
            y: this.height / 2,
            'text-anchor': 'middle',
            class: 'axis-text',
            'font-size': '16px',
            fill: '#666666'
        });
        text.textContent = 'No data available';
        svg.appendChild(text);
    }

    /**
     * Create SVG element with attributes
     */
    createSVGElement(type, attrs) {
        const elem = document.createElementNS('http://www.w3.org/2000/svg', type);
        Object.entries(attrs).forEach(([key, value]) => {
            if (key === 'class') {
                elem.setAttribute('class', value);
            } else {
                elem.setAttribute(key, value);
            }
        });
        return elem;
    }
}

// Application state and controller
class DashboardApp {
    constructor() {
        this.renderer = new ChartRenderer();
        this.districts = [];
        this.boces = [];
        this.currentDistrict = null;
        this.currentBoces = null;
        this.clusterView = false;
    }

    async init() {
        console.log('Initializing NYS District Dashboard...');
        
        try {
            // Load district index
            await this.loadDistricts();
            
            // Load sources
            await this.loadSources();
            
            // Setup event listeners
            this.setupEventListeners();
            
            console.log('Dashboard initialized successfully');
        } catch (error) {
            console.error('Error initializing dashboard:', error);
            this.showError('Failed to load dashboard data. Please try again later.');
        }
    }

    async loadDistricts() {
        try {
            const response = await fetch('spec/index.json');
            if (!response.ok) throw new Error('Failed to load district index');
            
            const data = await response.json();
            this.districts = data.districts || [];
            this.boces = data.boces || [];
            
            // Populate BOCES filter
            const bocesSelect = document.getElementById('bocesFilter');
            bocesSelect.innerHTML = '<option value="">All Regions</option>';
            
            const bocesNames = [...new Set(this.districts.map(d => d.boces))].filter(Boolean).sort();
            bocesNames.forEach(name => {
                const option = document.createElement('option');
                option.value = name;
                option.textContent = name;
                bocesSelect.appendChild(option);
            });
            
            // Populate district selector
            this.populateDistrictSelect(this.districts);
            
            console.log(`Loaded ${this.districts.length} districts, ${this.boces.length} BOCES regions`);
        } catch (error) {
            console.error('Error loading districts:', error);
            throw error;
        }
    }

    populateDistrictSelect(districts) {
        const select = document.getElementById('districtSelect');
        select.innerHTML = '<option value="">-- Select a District --</option>';
        
        districts.forEach(district => {
            const option = document.createElement('option');
            option.value = district.spec_file;
            const suffix = district.boces ? ` (${district.boces})` : '';
            option.textContent = district.name + suffix;
            select.appendChild(option);
        });
    }

    async loadSources() {
        try {
            const response = await fetch('data/sources.json');
            if (!response.ok) {
                console.warn('Sources file not found');
                return;
            }
            
            const sources = await response.json();
            this.displaySources(sources);
            
            // Update last update timestamp
            const lastUpdate = document.getElementById('lastUpdate');
            if (sources.length > 0) {
                const latestDate = sources
                    .map(s => new Date(s.fetched_at))
                    .sort((a, b) => b - a)[0];
                lastUpdate.textContent = latestDate.toLocaleString();
            }
        } catch (error) {
            console.error('Error loading sources:', error);
        }
    }

    displaySources(sources) {
        const container = document.getElementById('sourcesList');
        container.innerHTML = '';
        
        if (!sources || sources.length === 0) {
            container.innerHTML = '<p class="no-data">No source information available.</p>';
            return;
        }

        // Group sources by status
        const successSources = sources.filter(s => s.status === 'success');
        const failedSources = sources.filter(s => s.status === 'failed');

        // Display successful sources (limit to first 10 to avoid clutter)
        const displaySources = successSources.slice(0, 10);
        
        displaySources.forEach(source => {
            const div = document.createElement('div');
            div.className = 'source-item';
            
            const link = document.createElement('a');
            link.href = source.url;
            link.target = '_blank';
            link.textContent = this.truncateUrl(source.url);
            
            const meta = document.createElement('div');
            meta.className = 'source-meta';
            
            const status = document.createElement('span');
            status.className = `source-status ${source.status}`;
            status.textContent = source.status;
            
            meta.appendChild(status);
            
            if (source.fetched_at) {
                const time = document.createElement('span');
                time.textContent = ` • Fetched: ${new Date(source.fetched_at).toLocaleDateString()}`;
                meta.appendChild(time);
            }
            
            div.appendChild(link);
            div.appendChild(meta);
            container.appendChild(div);
        });

        if (successSources.length > 10) {
            const more = document.createElement('p');
            more.className = 'source-meta';
            more.textContent = `... and ${successSources.length - 10} more sources`;
            container.appendChild(more);
        }

        if (failedSources.length > 0) {
            const warning = document.createElement('p');
            warning.className = 'source-meta';
            warning.textContent = `Note: ${failedSources.length} source(s) failed to fetch`;
            warning.style.color = '#FF4D4D';
            container.appendChild(warning);
        }
    }

    truncateUrl(url) {
        if (url.length <= 80) return url;
        return url.substring(0, 77) + '...';
    }

    setupEventListeners() {
        const select = document.getElementById('districtSelect');
        select.addEventListener('change', (e) => {
            const specFile = e.target.value;
            this.clusterView = false;
            document.getElementById('showDistrictBtn').style.display = 'none';
            if (specFile) {
                this.loadDistrictSpec(specFile);
                // Find district boces and enable cluster button
                const district = this.districts.find(d => d.spec_file === specFile);
                if (district && district.boces) {
                    this.currentBoces = district.boces;
                    const clusterBtn = document.getElementById('showClusterBtn');
                    clusterBtn.disabled = false;
                    clusterBtn.textContent = `Compare ${district.boces} Districts`;
                }
            } else {
                this.clearCharts();
                document.getElementById('showClusterBtn').disabled = true;
                document.getElementById('showClusterBtn').textContent = 'Show BOCES Cluster Comparison';
            }
        });

        const bocesFilter = document.getElementById('bocesFilter');
        bocesFilter.addEventListener('change', (e) => {
            const boces = e.target.value;
            if (boces) {
                const filtered = this.districts.filter(d => d.boces === boces);
                this.populateDistrictSelect(filtered);
                this.currentBoces = boces;
                const clusterBtn = document.getElementById('showClusterBtn');
                clusterBtn.disabled = false;
                clusterBtn.textContent = `Compare ${boces} Districts`;
            } else {
                this.populateDistrictSelect(this.districts);
                this.currentBoces = null;
                document.getElementById('showClusterBtn').disabled = true;
                document.getElementById('showClusterBtn').textContent = 'Show BOCES Cluster Comparison';
            }
            this.clearCharts();
        });

        document.getElementById('showClusterBtn').addEventListener('click', () => {
            if (this.currentBoces) {
                this.loadBocesCluster(this.currentBoces);
            }
        });

        document.getElementById('showDistrictBtn').addEventListener('click', () => {
            this.clusterView = false;
            document.getElementById('showDistrictBtn').style.display = 'none';
            const specFile = document.getElementById('districtSelect').value;
            if (specFile) {
                this.loadDistrictSpec(specFile);
            } else {
                this.clearCharts();
            }
        });
    }

    async loadBocesCluster(bocesName) {
        const bocesEntry = this.boces.find(b => b.name === bocesName);
        if (!bocesEntry) {
            this.showError('BOCES cluster data not found.');
            return;
        }
        try {
            const response = await fetch(`spec/${bocesEntry.spec_file}`);
            if (!response.ok) throw new Error('Failed to load BOCES cluster spec');
            
            const spec = await response.json();
            this.clusterView = true;
            document.getElementById('showDistrictBtn').style.display = 'inline-block';
            this.renderCharts(spec);
        } catch (error) {
            console.error('Error loading BOCES cluster spec:', error);
            this.showError('Failed to load BOCES cluster data.');
        }
    }

    async loadDistrictSpec(specFile) {
        try {
            const response = await fetch(`spec/${specFile}`);
            if (!response.ok) throw new Error('Failed to load district spec');
            
            const spec = await response.json();
            this.renderCharts(spec);
        } catch (error) {
            console.error('Error loading district spec:', error);
            this.showError('Failed to load district data.');
        }
    }

    renderCharts(spec) {
        const container = document.getElementById('charts');
        container.innerHTML = '';

        // Render district snapshot header if data available
        this.renderSnapshot(spec);
        
        if (!spec.charts || spec.charts.length === 0) {
            container.innerHTML = '<p class="no-data">No charts available for this district.</p>';
            return;
        }

        spec.charts.forEach(chart => {
            const wrapper = document.createElement('div');
            wrapper.className = 'chart-wrapper';
            
            const title = document.createElement('h3');
            title.className = 'chart-title';
            title.textContent = chart.title;
            wrapper.appendChild(title);
            
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('class', 'chart-svg');
            wrapper.appendChild(svg);
            
            // Render chart based on type
            if (chart.type === 'line') {
                this.renderer.renderLineChart(svg, chart);
            } else if (chart.type === 'bar') {
                this.renderer.renderBarChart(svg, chart);
            }
            
            // Add annotation if present
            if (chart.annotation) {
                const annotation = document.createElement('p');
                annotation.className = 'chart-annotation';
                annotation.textContent = chart.annotation;
                wrapper.appendChild(annotation);
            }
            
            container.appendChild(wrapper);
        });
    }

    /**
     * Render a snapshot header with key district metrics
     */
    renderSnapshot(spec) {
        // Remove any existing snapshot
        const existing = document.getElementById('districtSnapshot');
        if (existing) existing.remove();

        if (!spec.charts || spec.charts.length === 0) return;

        const metrics = [];

        // Helper: find latest data point from a chart by title pattern
        const findLatest = (titlePattern, seriesField) => {
            const chart = spec.charts.find(c => titlePattern.test(c.title));
            if (!chart || !chart.data || chart.data.length === 0) return null;
            const field = chart.xAxis && chart.xAxis.field;
            if (!field) return null;
            const sorted = [...chart.data].sort((a, b) => {
                const av = a[field], bv = b[field];
                return typeof av === 'number' ? bv - av : String(bv).localeCompare(String(av));
            });
            const latest = sorted[0];
            const sField = seriesField || (chart.series && chart.series[0] && chart.series[0].field);
            if (!sField || latest[sField] === undefined) return null;
            return { value: latest[sField], year: latest[field] };
        };

        // ELA proficiency
        const ela = findLatest(/proficiency/i, 'ela');
        if (ela) metrics.push({ label: 'ELA Proficiency', value: ela.value + '%', year: ela.year });

        // Math proficiency
        const math = findLatest(/proficiency/i, 'math');
        if (math) metrics.push({ label: 'Math Proficiency', value: math.value + '%', year: math.year });

        // Graduation rate
        const grad = findLatest(/graduation/i, null);
        if (grad) metrics.push({ label: 'Graduation Rate', value: grad.value + '%', year: grad.year });

        // Total per-pupil spending (sum of categories for latest year)
        const expChart = spec.charts.find(c => /expenditure|spending/i.test(c.title));
        if (expChart && expChart.data && expChart.data.length > 0 && expChart.series) {
            const xField = expChart.xAxis && expChart.xAxis.field;
            if (xField) {
                const years = [...new Set(expChart.data.map(d => d[xField]))].sort((a, b) => {
                    return typeof a === 'number' ? b - a : String(b).localeCompare(String(a));
                });
                const latestYear = years[0];
                const latestRows = expChart.data.filter(d => d[xField] === latestYear);
                let total = 0;
                expChart.series.forEach(s => {
                    latestRows.forEach(r => { if (r[s.field] !== undefined) total += Number(r[s.field]) || 0; });
                });
                if (total > 0) metrics.push({ label: 'Per-Pupil Spending', value: '$' + total.toLocaleString(), year: latestYear });
            }
        }

        // Levy % change
        const levy = findLatest(/levy/i, null);
        if (levy) metrics.push({ label: 'Levy Change', value: levy.value + '%', year: levy.year });

        if (metrics.length === 0) return;

        const container = document.getElementById('charts');
        const section = document.createElement('div');
        section.id = 'districtSnapshot';
        section.className = 'snapshot-header';

        metrics.forEach(m => {
            const card = document.createElement('div');
            card.className = 'snapshot-card';

            const val = document.createElement('div');
            val.className = 'snapshot-value';
            val.textContent = m.value;
            card.appendChild(val);

            const lbl = document.createElement('div');
            lbl.className = 'snapshot-label';
            lbl.textContent = m.label;
            card.appendChild(lbl);

            const yr = document.createElement('div');
            yr.className = 'snapshot-year';
            yr.textContent = m.year;
            card.appendChild(yr);

            section.appendChild(card);
        });

        container.insertBefore(section, container.firstChild);
    }

    clearCharts() {
        const container = document.getElementById('charts');
        container.innerHTML = '<p class="no-data">Select a district to view data.</p>';
    }

    showError(message) {
        const container = document.getElementById('charts');
        container.innerHTML = `<p class="no-data" style="color: #FF4D4D;">${message}</p>`;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new DashboardApp();
    app.init();
});
