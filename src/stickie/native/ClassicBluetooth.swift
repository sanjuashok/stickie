// PM290C serial transport for macOS. Uses RFCOMM's own reliable flow control.
import Foundation
import IOBluetooth

func finish(_ value: [String: Any], code: Int32 = 0) -> Never {
    if let data = try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]) {
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data([10]))
    }
    exit(code)
}
func failure(_ message: String) -> Never { finish(["error": message], code: 1) }
func pairedPrinters() -> [IOBluetoothDevice] {
    (IOBluetoothDevice.pairedDevices() as? [IOBluetoothDevice] ?? []).filter {
        ($0.name ?? "").uppercased() == "PM290C"
    }
}
func pump(until deadline: Date, while condition: () -> Bool) {
    while condition() && Date() < deadline {
        RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.02))
    }
}

final class Receiver: NSObject, IOBluetoothRFCOMMChannelDelegate {
    var closed = false
    var data = Data()
    func rfcommChannelData(_ channel: IOBluetoothRFCOMMChannel!, data pointer: UnsafeMutableRawPointer!, length count: Int) {
        data.append(Data(bytes: pointer, count: count))
    }
    func rfcommChannelClosed(_ channel: IOBluetoothRFCOMMChannel!) { closed = true }
}

let args = CommandLine.arguments
let operation = args.count > 1 ? args[1] : ""
let requestedAddress = args.count > 2 ? args[2] : ""
guard ["list", "status", "info", "print", "self-test", "cancel"].contains(operation) else {
    failure("Unknown serial operation")
}
if operation == "list" {
    finish(["devices": pairedPrinters().map {
        ["name": $0.name ?? "PM290C", "address": $0.addressString ?? "", "paired": true] as [String: Any]
    }])
}
var job = Data()
if operation == "print" {
    job = FileHandle.standardInput.readDataToEndOfFile()
    guard !job.isEmpty && job.count <= 400_000 else { failure("Invalid print job size; no connection opened") }
}
let device: IOBluetoothDevice
if requestedAddress.isEmpty {
    let matches = pairedPrinters()
    guard matches.count == 1, let match = matches.first else {
        failure(matches.isEmpty
            ? "Pair PM290C in macOS System Settings → Bluetooth, then try again."
            : "Multiple paired PM290C printers found. Use --device with a MAC address from scan.")
    }
    device = match
} else {
    let normalized = requestedAddress.replacingOccurrences(of: "-", with: ":")
    guard normalized.range(of: "^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$", options: .regularExpression) != nil,
          let match = IOBluetoothDevice(addressString: normalized) else {
        failure("Bluetooth Classic requires a MAC address, not a BLE UUID. Use an address from scan.")
    }
    device = match
}
let receiver = Receiver()
var channel: IOBluetoothRFCOMMChannel?
// Channel 1 is verified in a successful Labelnize/PM290C HCI recording.
// Hardware testing validated synchronous open; async open did not complete reliably.
let openResult = device.openRFCOMMChannelSync(&channel, withChannelID: 1, delegate: receiver)
guard openResult == kIOReturnSuccess, let stream = channel else {
    device.closeConnection()
    failure("Could not open PM290C serial Bluetooth (error \(openResult)). Keep it on and disconnect other printer apps.")
}
let mtu = Int(stream.getMTU())
guard mtu > 0 else { stream.close(); failure("Printer returned an invalid serial packet size") }
func end(_ value: [String: Any], code: Int32 = 0) -> Never {
    stream.close()
    device.closeConnection()
    finish(value, code: code)
}
func stop(_ message: String) -> Never { end(["error": message], code: 1) }
func send(_ bytes: Data) {
    for offset in stride(from: 0, to: bytes.count, by: mtu) {
        if receiver.closed { stop("Printer disconnected. Check the paper before retrying.") }
        var part = bytes.subdata(in: offset..<min(offset + mtu, bytes.count))
        let result = part.withUnsafeMutableBytes { stream.writeSync($0.baseAddress, length: UInt16($0.count)) }
        if result != kIOReturnSuccess { stop("Serial write failed (\(result)). Check the paper before retrying.") }
    }
}
func queryStatus() -> UInt8 {
    receiver.data.removeAll()
    send(Data([0x1b, 0x21, 0x3f, 13, 10]))
    pump(until: Date(timeIntervalSinceNow: 5), while: { receiver.data.isEmpty && !receiver.closed })
    guard let status = receiver.data.first else { stop("Printer did not answer the readiness query") }
    if status != 0 { send(Data("ACK\r\n".utf8)) }
    receiver.data.removeAll()
    return status
}
if operation == "status" {
    end(["status": Int(queryStatus())])
}
if operation == "cancel" {
    // The app's serial writer appends a newline to its ESC command.
    send(Data("ESC\r\n".utf8))
    pump(until: Date(timeIntervalSinceNow: 1), while: { !receiver.closed })
    end(["status": Int(queryStatus()), "cancel_requested": true])
}
if operation == "info" {
    send(Data("CONFIG?\r\n".utf8))
    pump(until: Date(timeIntervalSinceNow: 5), while: {
        !receiver.data.suffix(2).elementsEqual([13, 10]) && !receiver.closed
    })
    guard !receiver.data.isEmpty else { stop("Printer did not answer the identity query") }
    end(["address": device.addressString ?? "", "transport": "Bluetooth Classic RFCOMM",
         "channel": 1, "mtu": mtu, "config_hex": receiver.data.map { String(format: "%02x", $0) }.joined()])
}
let state = queryStatus()
guard state == 0 else { end(["status": Int(state), "not_sent": true], code: 2) }
if operation == "self-test" {
    send(Data("SELFTEST\r\n".utf8))
    pump(until: Date(timeIntervalSinceNow: 2), while: { !receiver.closed })
    end(["self_test_requested": true])
}

var completed = false
// RFCOMM is a byte stream: retain partial replies across callbacks.
func consumePrintReplies() {
    while let first = receiver.data.first {
        if first == 0x63 {
            guard receiver.data.count >= 2 else { return }
            let second = receiver.data[receiver.data.startIndex + 1]
            if second == 0 {
                receiver.data.removeFirst(2)
                completed = true
            } else if second == 0x20 {
                // Next-copy request is not completion. Acknowledge the full
                // five-byte form used by this printer, retaining partial data.
                guard receiver.data.count >= 5 else { return }
                receiver.data.removeFirst(5)
                send(Data("ACK\r\n".utf8))
            } else { stop("Unexpected print reply; check the paper before retrying.") }
        } else if first == 0xf0 {
            guard receiver.data.count >= 4 else { return }
            receiver.data.removeFirst(4)
        } else {
            receiver.data.removeFirst()
            if first != 0 && first != 32 {
                send(Data("ACK\r\n".utf8))
                end(["status": Int(first), "during_print": true], code: 2)
            }
        }
    }
}
var sent = 0
for offset in stride(from: 0, to: job.count, by: mtu) {
    consumePrintReplies()
    if completed { stop("Printer completed before all image data was sent; check the paper.") }
    let endOffset = min(offset + mtu, job.count)
    send(job.subdata(in: offset..<endOffset))
    sent = endOffset
    // Let the delegate deliver faults and completion between serial writes.
    RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.001))
}
let waitSeconds = args.count > 3 ? (Double(args[3]) ?? 30) : 30
let deadline = Date(timeIntervalSinceNow: max(15, min(360, waitSeconds)))
while !completed && Date() < deadline && !receiver.closed {
    consumePrintReplies()
    if !completed { RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.02)) }
}
consumePrintReplies()
guard completed else { stop("Print sent, but completion was not confirmed. Check the paper before retrying.") }
end(["complete": true, "bytes_sent": sent, "mtu": mtu])
