import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const CONFIG_PATH = path.join(process.cwd(), '..', 'config', 'sender_filters.json');

// GET settings
export async function GET() {
  try {
    const configContent = fs.readFileSync(CONFIG_PATH, 'utf-8');
    const config = JSON.parse(configContent);
    
    return NextResponse.json({
      success: true,
      config,
    });
    
  } catch (error: any) {
    console.error('Error reading settings:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}

// PUT - Update settings
export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Validate the config structure
    if (!body.skip_drafting || !body.always_draft || !body.override) {
      return NextResponse.json(
        { success: false, error: 'Invalid config structure' },
        { status: 400 }
      );
    }
    
    // Write the new config
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(body, null, 2));
    
    return NextResponse.json({
      success: true,
      message: 'Settings updated successfully',
    });
    
  } catch (error: any) {
    console.error('Error updating settings:', error);
    return NextResponse.json(
      { success: false, error: error.message },
      { status: 500 }
    );
  }
}
