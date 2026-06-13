import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';

export default function Footer(){
    return (
        <div>
            <Link to="#">contact us</Link>
            <p>This is a test footer, we can change it later on </p>
        </div>

    );
}
