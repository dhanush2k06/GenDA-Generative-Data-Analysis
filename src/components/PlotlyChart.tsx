import { useEffect, useRef } from 'react';

declare global {
  interface Window {
    Plotly?: any;
  }
}

interface PlotlyChartProps {
  spec: {
    data: any[];
    layout?: any;
    config?: any;
  };
  height?: number | string;
  className?: string;
}

export function PlotlyChart({ spec, height = 380, className = '' }: PlotlyChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let pollInterval: ReturnType<typeof setInterval> | null = null;

    const renderChart = () => {
      if (window.Plotly && containerRef.current) {
        const responsiveLayout = {
          autosize: true,
          ...spec.layout,
        };

        const config = {
          responsive: true,
          displayModeBar: false,
          ...spec.config,
        };

        window.Plotly.newPlot(
          containerRef.current,
          spec.data || [],
          responsiveLayout,
          config
        );
      }
    };

    if (window.Plotly) {
      renderChart();
    } else {
      // Poll briefly for CDN script load if needed (max 5 seconds)
      let retries = 0;
      pollInterval = setInterval(() => {
        retries++;
        if (window.Plotly) {
          clearInterval(pollInterval!);
          pollInterval = null;
          renderChart();
        } else if (retries > 50) {
          clearInterval(pollInterval!);
          pollInterval = null;
        }
      }, 100);
    }

    const handleResize = () => {
      if (window.Plotly && containerRef.current) {
        window.Plotly.Plots.resize(containerRef.current);
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      if (pollInterval !== null) {
        clearInterval(pollInterval);
      }
      window.removeEventListener('resize', handleResize);
      if (window.Plotly && containerRef.current) {
        window.Plotly.purge(containerRef.current);
      }
    };
  }, [spec]);

  return (
    <div
      ref={containerRef}
      style={{ height, minHeight: 320, width: '100%' }}
      className={`rounded-lg overflow-hidden ${className}`}
    />
  );
}
