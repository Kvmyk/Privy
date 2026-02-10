#!/bin/bash
set -e


VERSION="1.4.0"
ARCH="amd64"
PKG_NAME="privy"
FULL_NAME="${PKG_NAME}_${VERSION}-1_${ARCH}"
TEMP_BUILD_ROOT="${HOME}/.privy_build_temp"
BUILD_DIR="${TEMP_BUILD_ROOT}/${FULL_NAME}"

echo "Building Privy v${VERSION} package for Debian/Ubuntu..."

rm -rf "${TEMP_BUILD_ROOT}"
mkdir -p "${TEMP_BUILD_ROOT}"

if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

echo "Compiling Python source to standalone binary..."

echo "from privy.main import main; main()" > build_entry.py

pyinstaller --clean --onefile --name privy build_entry.py

echo "Compiling PrivyPM to standalone binary..."
echo "from privy.pm import main; main()" > build_pm_entry.py
pyinstaller --clean --onefile --name privypm build_pm_entry.py

rm build_entry.py build_pm_entry.py

echo "Preparing package structure in ${BUILD_DIR}..."
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/local/bin"
mkdir -p "${BUILD_DIR}/usr/local/share/privy/docs"
mkdir -p "${BUILD_DIR}/usr/share/doc/${PKG_NAME}"

echo "Copying files..."
cp dist/privy "${BUILD_DIR}/usr/local/bin/"
cp dist/privypm "${BUILD_DIR}/usr/local/bin/"
chmod 755 "${BUILD_DIR}/usr/local/bin/privy"
chmod 755 "${BUILD_DIR}/usr/local/bin/privypm"

cp debian-build/${FULL_NAME}/DEBIAN/control "${BUILD_DIR}/DEBIAN/control"
chmod 755 "${BUILD_DIR}/DEBIAN"
chmod 644 "${BUILD_DIR}/DEBIAN/control"

cp LICENSE "${BUILD_DIR}/usr/share/doc/${PKG_NAME}/copyright"
if [ -f README.md ]; then
    cp README.md "${BUILD_DIR}/usr/share/doc/${PKG_NAME}/README.md"
fi

if [ -d docs ]; then
    cp docs/* "${BUILD_DIR}/usr/local/share/privy/docs/"
fi

echo "Building .deb package..."
dpkg-deb --build "${BUILD_DIR}"

echo "Moving .deb to project directory..."
mv "${TEMP_BUILD_ROOT}/${FULL_NAME}.deb" .
echo "Done! Package saved to: ${FULL_NAME}.deb"

rm -rf "${TEMP_BUILD_ROOT}"
