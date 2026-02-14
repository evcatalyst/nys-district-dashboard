// NYS District Dashboard - Main Application
// Lightweight chart renderer using vanilla JavaScript and SVG

class ChartRenderer {
    constructor() {
        this.margin = { top: 40, right: 80, bottom: 60, left: 60 };
        this.width = 800;
        this.height = 400;
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

        // Draw series
        series.forEach((s, idx) => {
            const seriesData = data.filter(d => {
                if (!s.filter) return true;
                return Object.entries(s.filter).every(([key, val]) => d[key] === val);
            });

            if (seriesData.length === 0) return;

            // Sort by x value
            if (isNumericX) {
                seriesData.sort((a, b) => a[xAxis.field] - b[xAxis.field]);
            } else {
                seriesData.sort((a, b) => uniqueXValues.indexOf(String(a[xAxis.field])) - uniqueXValues.indexOf(String(b[xAxis.field])));
            }

            // Draw line
            const points = seriesData.map(d => ({
                x: xScale(d[xAxis.field]),
                y: yScale(d[s.field])
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
                fill: 'none'
            });
            svg.appendChild(path);

            // Draw data points
            points.forEach(p => {
                const circle = this.createSVGElement('circle', {
                    cx: p.x,
                    cy: p.y,
                    r: 4,
                    fill: s.color || '#1f77b4',
                    class: 'data-point'
                });
                svg.appendChild(circle);
            });
        });

        // Draw legend
        this.drawLegend(svg, series, this.width - this.margin.right - 10);
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
            fill: '#666'
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
            warning.style.color = '#721c24';
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

    clearCharts() {
        const container = document.getElementById('charts');
        container.innerHTML = '<p class="no-data">Select a district to view data.</p>';
    }

    showError(message) {
        const container = document.getElementById('charts');
        container.innerHTML = `<p class="no-data" style="color: #721c24;">${message}</p>`;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new DashboardApp();
    app.init();
});
