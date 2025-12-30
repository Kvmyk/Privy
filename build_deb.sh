#!/bin/bash
set -e

# Configuration
VERSION="1.4.0"
ARCH="amd64"
PKG_NAME="privy"
FULL_NAME="${PKG_NAME}_${VERSION}-1_${ARCH}"
# Use a temp dir in HOME to ensure linux permissions work (fix for WSL /mnt mounts)
TEMP_BUILD_ROOT="${HOME}/.privy_build_temp"
BUILD_DIR="${TEMP_BUILD_ROOT}/${FULL_NAME}"

echo "Building Privy v${VERSION} package for Debian/Ubuntu..."

# Cleanup previous temp build
rm -rf "${TEMP_BUILD_ROOT}"
mkdir -p "${TEMP_BUILD_ROOT}"

# 1. Check/Install PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# 2. Build Binary
echo "Compiling Python source to standalone binary..."
# --onefile: Create a single executable
# --name: Output name
# --clean: Clean cache
pyinstaller --clean --onefile --name privy privy/main.py

# 3. Prepare Package Structure
echo "Preparing package structure in ${BUILD_DIR}..."
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/local/bin"
mkdir -p "${BUILD_DIR}/usr/share/doc/${PKG_NAME}"

# 4. Copy Files
echo "Copying files..."
cp dist/privy "${BUILD_DIR}/usr/local/bin/"
chmod 755 "${BUILD_DIR}/usr/local/bin/privy"

# Copy control file from local project to temp build dir
cp debian-build/${FULL_NAME}/DEBIAN/control "${BUILD_DIR}/DEBIAN/control"
chmod 755 "${BUILD_DIR}/DEBIAN"
chmod 644 "${BUILD_DIR}/DEBIAN/control"

cp LICENSE "${BUILD_DIR}/usr/share/doc/${PKG_NAME}/copyright"
if [ -f README.md ]; then
    cp README.md "${BUILD_DIR}/usr/share/doc/${PKG_NAME}/README.md"
fi

# 5. Build .deb
echo "Building .deb package..."
dpkg-deb --build "${BUILD_DIR}"

# 6. Move result back
echo "Moving .deb to project directory..."
mv "${TEMP_BUILD_ROOT}/${FULL_NAME}.deb" .
echo "Done! Package saved to: ${FULL_NAME}.deb"

# Cleanup
rm -rf "${TEMP_BUILD_ROOT}"
