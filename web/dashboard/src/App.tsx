import { useState } from 'react'
import MicControls from './components/MicControls'
import EventLog from './components/EventLog'
import './App.css'

function App() {
  const [events, setEvents] = useState<Array<{type: string, timestamp: string, data?: any}>>([])
  const [isConnected, setIsConnected] = useState(false)

  const addEvent = (type: string, data?: any) => {
    setEvents(prev => [...prev, {
      type,
      timestamp: new Date().toLocaleTimeString(),
      data
    }])
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>TOM v3.0 - Realtime Dashboard</h1>
        <p>Status: {isConnected ? '🟢 Verbunden' : '🔴 Getrennt'}</p>
      </header>
      
      <main className="app-main">
        <div className="controls-panel">
          <MicControls 
            onConnect={(connected) => setIsConnected(connected)}
            onEvent={addEvent}
          />
        </div>
        
        <div className="events-panel">
          <EventLog events={events} />
        </div>
      </main>
    </div>
  )
}

export default App
