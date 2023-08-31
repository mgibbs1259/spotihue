import './App.css';
import GreenBorderButton from './components/GreenBorderButton';

function App() {
  const handleApiRequest = async (apiEndPoint) => {
    try {
      const response = await fetch(apiEndPoint);
      const data = await response.json();
      console.log(data); // Handle the API response data
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  return (
    <div className="app">
      <div className="app-container">     
        <div>
          <GreenBorderButton text="configure" fontSize="40px" />
        </div>
        <div>
          <GreenBorderButton text="configure" fontSize="40px" />
        </div>
      </div>
    </div>
  );
}

export default App;
