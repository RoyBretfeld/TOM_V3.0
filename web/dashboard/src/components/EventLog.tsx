import React from 'react';
import { EventLogEntry } from '../types/events';
import './EventLog.css';

interface EventLogProps {
  events: EventLogEntry[];
}

const EventLog: React.FC<EventLogProps> = ({ events }) => {
  const getEventIcon = (type: string): string => {
    switch (type) {
      case 'connected': return '🔗';
      case 'disconnected': return '🔌';
      case 'streaming_started': return '🎤';
      case 'streaming_stopped': return '⏸️';
      case 'audio_chunk': return '📡';
      case 'stt_partial': return '🗣️';
      case 'stt_final': return '✅';
      case 'llm_token': return '🤖';
      case 'tts_audio': return '🔊';
      case 'turn_end': return '🏁';
      case 'ping': return '📡';
      case 'pong': return '📡';
      case 'error': return '❌';
      default: return '📄';
    }
  };

  const getEventColor = (type: string): string => {
    switch (type) {
      case 'connected': return '#4CAF50';
      case 'disconnected': return '#f44336';
      case 'streaming_started': return '#2196F3';
      case 'streaming_stopped': return '#FF9800';
      case 'audio_chunk': return '#9C27B0';
      case 'stt_partial': return '#FFC107';
      case 'stt_final': return '#4CAF50';
      case 'llm_token': return '#00BCD4';
      case 'tts_audio': return '#795548';
      case 'turn_end': return '#607D8B';
      case 'ping': return '#E91E63';
      case 'pong': return '#E91E63';
      case 'error': return '#f44336';
      default: return '#666';
    }
  };

  const formatEventData = (data: any): string => {
    if (!data) return '';
    
    if (typeof data === 'string') {
      return data.length > 50 ? data.substring(0, 50) + '...' : data;
    }
    
    if (typeof data === 'object') {
      const keys = Object.keys(data);
      if (keys.length === 0) return '';
      
      const preview = keys.slice(0, 2).map(key => `${key}: ${data[key]}`).join(', ');
      return keys.length > 2 ? preview + '...' : preview;
    }
    
    return String(data);
  };

  return (
    <div className="event-log">
      <div className="event-log-header">
        <h2>Event-Log</h2>
        <span className="event-count">{events.length} Events</span>
      </div>
      
      <div className="event-list">
        {events.length === 0 ? (
          <div className="no-events">
            <p>Keine Events vorhanden</p>
            <p className="hint">Verbinden und Streaming starten, um Events zu sehen</p>
          </div>
        ) : (
          events.slice().reverse().map((event, index) => (
            <div key={index} className="event-item">
              <div className="event-icon" style={{ color: getEventColor(event.type) }}>
                {getEventIcon(event.type)}
              </div>
              <div className="event-content">
                <div className="event-header">
                  <span className="event-type">{event.type}</span>
                  <span className="event-timestamp">{event.timestamp}</span>
                </div>
                {event.data && (
                  <div className="event-data">
                    {formatEventData(event.data)}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default EventLog;
