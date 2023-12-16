import React, { useState, useEffect } from 'react';
import { useGetData } from '../hooks/useGetData';
import ButtonContainer from '../components/ButtonContainer';
import SelectLightButton from '../components/SelectLightButton';
import PrimaryButton from '../components/PrimaryButton';

function SelectLightsContainer() {
    const [isButtonDisabled, setIsButtonDisabled] = useState(false); 
    const [lightsData, setLightsData] = useState([]);
    const [selectedLights, setSelectedLights] = useState([]);
    
    const { data } = useGetData('http://localhost:8000/available-lights'); 

    useEffect(() => {
        if (data && data.data) {
          // Ensure data and data.data exist before extracting the values
          const lightNames = data.data.map(item => item.light_name);
          setLightsData(lightNames);
        }
      }, [data]);
    
    const handleLightButtonClick = (lightName) => {
    if (selectedLights.includes(lightName)) {
        setSelectedLights(selectedLights.filter(name => name !== lightName));
    } else {
        setSelectedLights([...selectedLights, lightName]);
    }
    };
    
    const handleDoneButtonClick = (lightName) => {
        // Store selected light names in session storage
        selectedLights.forEach((lightName, index) => {
        sessionStorage.setItem(`light${index + 1}`, lightName);
        });
  
        setIsButtonDisabled(true);
    };

    return (
        <ButtonContainer>
        {lightsData.map((value, index) => (
            <SelectLightButton key={index} lightName={value} onClick={handleLightButtonClick}></SelectLightButton>
        ))}
          <PrimaryButton text="Done" fontSize="40px" disabled={isButtonDisabled} onClick={handleDoneButtonClick} />
        </ButtonContainer>
        );
}
    
export default SelectLightsContainer;