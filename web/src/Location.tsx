interface LocationProps {
  name: string;
  country?: string;
  type: string;
  clickHandler?: () => void;
}

export default function Location({ name, country, type, clickHandler }: LocationProps) {
  return (
    <div onClick={clickHandler} className={`p-8 flex flex-col items-center justify-center border-b border-gray-200  hover:bg-gray-50 cursor-pointer`}>
      <p className="text-sm mb-0.5 text-gray-700">{type}</p>
      <h2 className="font-semibold text-center capitalize">{name}</h2>
      <p className="text-sm text-gray-500 text-center">{country}</p>
    </div>
  )
}
